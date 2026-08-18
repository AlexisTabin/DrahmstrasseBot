"""End-to-end integration tests: real Lambda entry point, real DynamoDB
(via moto), real bot wiring. Only the two genuinely external services are
stubbed out: the Telegram API (bot.bot.send_message/... replaced with
AsyncMock) and the Open-Meteo weather call used by /arrosage.

This mirrors what the deploy.yml smoke test checks against the deployed
Lambda, but runs offline against the PR's own code — see
.github/workflows/deploy.yml and .claude/docs/ for context on why the
smoke test itself can't run on a PR (it invokes the already-deployed
Lambda, not the PR's code).
"""
import datetime
import json

import boto3
import pytest
from moto import mock_aws
from unittest.mock import AsyncMock, patch

import src.chores as chores
import src.cendrier as cendrier
import src.menage as menage
import src.plants as plants
from src import main
from src.drahmbot import Drahmbot, TELEGRAM_USER_MAP, colocataires

PROD_CHAT_ID = -1001633433047
TABLE_NAME = "drahmstrassebot-chores"

# Mirrors infra/eventbridge.tf's `locals.schedules[*].command`.
EVENTBRIDGE_COMMANDS = [
    "/whoishere@DrahmstrasseBot",
    "/roles",
    "/papier@DrahmstrasseBot",
    "/carton@DrahmstrasseBot",
    "/reminder@DrahmstrasseBot",
    "/recap@DrahmstrasseBot",
    "/arrosage@DrahmstrasseBot",
]


def _eventbridge_event(command, chat_id=PROD_CHAT_ID):
    """Build the exact payload shape EventBridge sends (no 'from' field)."""
    body = {
        "message": {
            "chat": {"id": chat_id},
            "text": command,
            "entities": [{"type": "bot_command", "offset": 0, "length": len(command)}],
        }
    }
    return {"body": json.dumps(body)}


def _webhook_event(text, user_id, chat_id=PROD_CHAT_ID, message_id=1):
    """Build a webhook-shaped payload for a message from a real colocataire."""
    command_len = len(text.split()[0])
    body = {
        "update_id": message_id,
        "message": {
            "message_id": message_id,
            "date": 0,
            "chat": {"id": chat_id, "type": "group"},
            "from": {"id": user_id, "is_bot": False, "first_name": "Test"},
            "text": text,
            "entities": [{"type": "bot_command", "offset": 0, "length": command_len}],
        },
    }
    return {"body": json.dumps(body)}


def _callback_event(data, user_id, chat_id=PROD_CHAT_ID, message_id=1):
    """Build a webhook-shaped payload for an inline keyboard button click."""
    body = {
        "update_id": message_id + 1000,
        "callback_query": {
            "id": f"cb{message_id}",
            "from": {"id": user_id, "is_bot": False, "first_name": "Test"},
            "chat_instance": "1",
            "message": {
                "message_id": message_id,
                "date": 0,
                "chat": {"id": chat_id, "type": "group"},
                "text": "placeholder",
            },
            "data": data,
        },
    }
    return {"body": json.dumps(body)}


@pytest.fixture(autouse=True)
def dynamodb_table(monkeypatch):
    """Fresh in-memory DynamoDB table per test, matching the prod schema."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-north-1")

    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="eu-north-1")
        dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[{"AttributeName": "week_key", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "week_key", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        chores._table = None
        plants._table = None
        cendrier._table = None
        yield
        chores._table = None
        plants._table = None
        cendrier._table = None


@pytest.fixture
def bot():
    """A fresh Drahmbot singleton with the real Telegram API calls stubbed out."""
    Drahmbot._instance = None
    instance = Drahmbot(token="123456:fake-token", chat_id=PROD_CHAT_ID)
    instance.bot.send_message = AsyncMock()
    instance.bot.send_poll = AsyncMock()
    instance.bot.edit_message_text = AsyncMock()
    instance.bot.answer_callback_query = AsyncMock()
    yield instance
    Drahmbot._instance = None


@pytest.mark.asyncio
@patch("src.drahmbot.weather.get_zurich_max_temp_today", return_value=30.0)
@pytest.mark.parametrize("command", EVENTBRIDGE_COMMANDS)
async def test_eventbridge_command_runs_without_error(mock_temp, bot, command):
    """Mirrors the deploy.yml smoke test: fire every scheduled command through
    the real handler (real DynamoDB via moto, real bot wiring) and assert it
    completes without a Lambda-level error and actually talks to Telegram."""
    event = _eventbridge_event(command)

    response = await main.handler(event, {})

    assert response["statusCode"] == 200
    assert bot.bot.send_message.called or bot.bot.send_poll.called


@pytest.mark.asyncio
async def test_frigo_write_path_round_trip(bot):
    """A roommate who isn't assigned CUISINE this week still gets credit for
    /frigo, and /recap reflects it — exercises the full write path through
    real DynamoDB (moto), not just the individual handler functions."""
    assignments = menage.get_role_assignments(colocataires)
    cuisine_person = assignments["CUISINE"]
    helper = next(p for p in colocataires if p != cuisine_person)
    helper_id = next(uid for uid, name in TELEGRAM_USER_MAP.items() if name == helper)
    week_num = datetime.date.today().isocalendar()[1]

    # 1. Helper runs /frigo — gets a keyboard, nothing marked yet.
    await main.handler(_webhook_event("/frigo", helper_id), {})
    assert bot.bot.send_message.called

    # 2. Helper clicks the button to mark it done.
    await main.handler(_callback_event(f"subtask:{week_num}:frigo", helper_id), {})
    bot.bot.edit_message_text.assert_called_once()
    edited_text = bot.bot.edit_message_text.call_args[0][0]
    assert helper in edited_text

    # 3. DynamoDB actually persisted it.
    role_data = chores.get_week_status().get("CUISINE", {})
    assert role_data["subtasks"]["frigo"]["by"] == helper

    # 4. /recap credits the helper (recap text is the 2nd-to-last call; /recap also sends a leaderboard message).
    await main.handler(_eventbridge_event("/recap@DrahmstrasseBot"), {})
    recap_text = bot.bot.send_message.call_args_list[-2][0][1]
    assert f"frigo fait par {helper}" in recap_text
    assert f"(pas {cuisine_person})" in recap_text


@pytest.mark.asyncio
async def test_plandetravail_counter_write_path_round_trip(bot):
    """Exercises increment_subtask_counter's real DynamoDB UpdateExpression
    (via moto) end to end, including the ReturnValues read-back and the "by"/
    "at" attribute-name aliasing — unit tests mock table.update_item entirely
    and can't catch a DynamoDB-rejected expression (e.g. an unaliased
    reserved word), only a real update against moto's DynamoDB emulation
    can. Two different people press "+1" so /recap must credit both."""
    week_num = datetime.date.today().isocalendar()[1]
    timon_id = next(uid for uid, name in TELEGRAM_USER_MAP.items() if name == "Timon")
    lea_id = next(uid for uid, name in TELEGRAM_USER_MAP.items() if name == "Léa")

    # 1. Timon runs /plandetravail and presses "+1" once.
    await main.handler(_webhook_event("/plandetravail", timon_id), {})
    assert bot.bot.send_message.called
    await main.handler(_callback_event(f"counter:{week_num}:plandetravail", timon_id), {})
    bot.bot.edit_message_text.assert_called_once()
    assert "1x" in bot.bot.edit_message_text.call_args[0][0]

    # 2. Léa presses "+1" too (via the same open message's button).
    await main.handler(_callback_event(f"counter:{week_num}:plandetravail", lea_id), {})
    assert "2x" in bot.bot.edit_message_text.call_args_list[1][0][0]

    # 3. DynamoDB actually persisted the count and both doers.
    role_data = chores.get_week_status().get("CUISINE", {})
    sub_data = role_data["subtasks"]["plan de travail"]
    assert sub_data["count"] == 2
    assert sub_data["doers"] == {"Timon", "Léa"}

    # 4. /recap credits both Timon and Léa, not just whoever pressed "+1" last (recap text is the 2nd-to-last call; /recap also sends a leaderboard message).
    assignments = menage.get_role_assignments(colocataires)
    cuisine_person = assignments["CUISINE"]
    await main.handler(_eventbridge_event("/recap@DrahmstrasseBot"), {})
    recap_text = bot.bot.send_message.call_args_list[-2][0][1]
    if cuisine_person == "Timon":
        assert "plan de travail fait par Léa" in recap_text
    elif cuisine_person == "Léa":
        assert "plan de travail fait par Timon" in recap_text
    else:
        assert "plan de travail fait par Léa, Timon" in recap_text
