import random


MONDAY_SAME_ROLES = [
    "Encore une semaine avec les mêmes rôles ehehe",
    "Rebelote, on garde la même équipe cette semaine",
    "Pas de changement, mêmes rôles que la semaine dernière",
    "On recycle les rôles pour encore une semaine ehehe",
    "Même casting que la semaine passée, bon courage",
    "Rôles inchangés, on continue sur la lancée",
    "Deuxième service avec les mêmes rôles, bon app",
    "Les rôles ont décidé de rester, on fait avec ehehe",
    "Copier-coller des rôles de la semaine dernière",
    "Même équipe, même combat, même poussière",
    "La roue du ménage a oublié de tourner cette semaine",
    "Bis repetita placent : rôles identiques ehehe",
    "Les rôles font grève du tournage, même dispo que la semaine passée",
    "Toujours les mêmes au charbon cette semaine, courage",
]

MONDAY_NEW_ROLES = [
    "Coucou, changement de rôles pour le ménage ehehe",
    "Pouet, on redistribue les tâches cette semaine",
    "Nouveaux rôles de ménage, let's go",
    "Nouvelle semaine, nouveaux rôles ehehe",
    "Changement d'équipe pour le ménage, allez zou",
    "Hop, on tourne les rôles ehehe",
    "Pouet pouet, la roue du ménage a tourné",
    "Redistribution des cartes, voilà les nouveaux rôles",
    "La rotation a frappé, nouveaux rôles pour tout le monde",
    "Reshuffle hebdomadaire, voici les nouveaux rôles ehehe",
    "Changement de crémerie, nouveaux rôles cette semaine",
    "Rebrassage complet, voilà qui fait quoi",
    "Nouvelle donne pour le ménage, que les jeux commencent",
    "La roulette du ménage a parlé ehehe",
    "Coucou l'ekip, on change d'affectation cette semaine",
]

THURSDAY_ALL_DONE = [
    "Rappel du jeudi : tout est fait cette semaine, bravo !",
    "Jeudi check : tout est nickel, bravo l'ekip",
    "Rien à rappeler aujourd'hui, la coloc a tout cartonné",
    "Aucun rappel ce jeudi, tout est déjà fait. Bravo !",
    "Jeudi : rien à signaler, tout est fait. Propre !",
    "Jeudi tranquille : tout est bouclé, bravo la coloc",
    "Jeudi sans stress, tout est fait, chapeau bas",
    "La coloc a tout géré avant jeudi, respect ehehe",
    "Rien à voir ce jeudi, circulez, c'est déjà propre",
    "Jeudi zéro rappel : vous êtes des machines",
    "Tout est fait, le bot est au chômage technique ehehe",
    "Jeudi : le ménage a déjà été ménagé. Bravo",
    "Aucune tâche en retard, c'est beau à voir",
    "Coloc modèle, tout est fait avant le rappel. Pouet !",
    "Jeudi propre sur lui : rien à signaler, bravo",
]

THURSDAY_REMINDER_HEADER = [
    "Rappel du jeudi — tâches pas encore faites :",
    "Pouet, petit rappel du jeudi, il reste :",
    "Jeudi check — il manque encore ça :",
    "Coucou, petit retard sur ces tâches :",
    "Ehehe, le jeudi est là, et ça non plus n'est pas fait :",
    "Rappel amical : ça traîne un peu du côté de :",
    "Le bot passe en mode nag, il reste :",
    "Jeudi, jour du rappel — pas encore fait :",
    "Alerte poussière niveau jaune, il reste :",
    "Toc toc, c'est le jeudi — à faire encore :",
    "Petit coup de pouce du jeudi, il reste :",
    "Hey l'ekip, y a encore du boulot :",
    "Rappel de mi-semaine, pas encore coché :",
    "Le bot vous rappelle gentiment qu'il reste :",
]

THURSDAY_DONE_SECTION = [
    "Déjà fait :",
    "Déjà bouclé (bravo) :",
    "Au tableau d'honneur :",
    "Déjà plié :",
    "Dans la boîte :",
    "Déjà OK :",
    "Tip top, déjà fait :",
    "Nickel, c'est fait :",
    "Déjà coché :",
    "Check, c'est fait :",
]

SUNDAY_RECAP_HEADER = [
    "Récap de la semaine :",
    "Bilan du dimanche soir :",
    "Debrief de la semaine :",
    "Petit récap dominical :",
    "Récap hebdo, let's go :",
    "Dimanche soir, heure du bilan :",
    "Et voilà le debrief de la semaine :",
    "Rétrospective ménage de la semaine :",
    "Pouet, c'est l'heure du récap :",
    "Dimanche récap, accrochez-vous :",
    "Bilan avant de repartir pour une semaine :",
    "Récap du week-end, qui a assuré :",
]

STATS_HEADER = [
    "Stats :",
    "Tableau d'honneur :",
    "Leaderboard ménage :",
    "Podium de la coloc :",
    "Classement des pros du ménage :",
    "Stats, pour les curieux :",
]

STATS_EMPTY = [
    "Pas encore de stats !",
    "Rien à compter pour l'instant, revenez plus tard",
    "Les stats sont désespérément vides",
    "Aucune stat à se mettre sous la dent",
    "C'est le désert niveau stats, bougez-vous ehehe",
]


def pick(phrases):
    """Return a random phrase from the given list."""
    return random.choice(phrases)
