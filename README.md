# LLM SQL Bot - Service Client E-commerce

## Objectif
Ce projet implémente un assistant capable de répondre à des questions sur des commandes clients à partir d'une base SQLite (`orders.db`), avec des garde-fous de sécurité.

Le flux principal est dans [llm-sql.ipynb](/Users/jadedupont/projects/blentAI/llm/projets-hands-on/blentai-llm-cs/llm-sql.ipynb).

## Architecture fonctionnelle
1. Routage sémantique de la demande utilisateur:
- `order_info`: demande d'information sur commande.
- `order_help`: demande d'aide (annulation, modification, conseiller), redirigée vers un humain.
- `out_of_scope`: hors périmètre service client commandes.

2. Authentification applicative:
- entrée: `email`, `first_name`, `last_name`.
- résolution backend du `user_id` dans la table `users`.
- si 0 ou plusieurs correspondances: arrêt du traitement.

3. Génération SQL (LLM):
- génération d'une requête de lecture ciblée.
- obligation de filtrer sur `user_id` authentifié.

4. Validation de sécurité SQL:
- requêtes `SELECT` uniquement.
- blocage des patterns d'injection courants (`OR`, `UNION`, commentaires SQL, `;`).
- vérification stricte du filtre `user_id`.

5. Exécution SQL puis reformulation de la réponse.

## Sécurité
La fonction [security.py](/Users/jadedupont/projects/blentAI/llm/projets-hands-on/blentai-llm-cs/security.py) applique notamment:
- rejet si la requête n'est pas un `SELECT`.
- rejet si `WHERE` absent.
- rejet de patterns à risque (`OR`, `UNION`, `--`, `/* */`, `;`).
- obligation de présence de `user_id = <authenticated_user_id>`.
- rejet si un autre `user_id` apparaît dans la clause `WHERE`.

## Tests
### 1. Tests unitaires sécurité
Fichier: [tests/test_security.py](/Users/jadedupont/projects/blentAI/llm/projets-hands-on/blentai-llm-cs/tests/test_security.py)

Couvre:
- cas valides (`user_id` simple et avec alias),
- erreurs de filtre (`WHERE` absent, mauvais `user_id`),
- tentatives d'injection (`OR`, `UNION`, commentaires, multi-statements).

### 2. Tests d'intégration du flux
Fichier: [tests/test_run_query.py](/Users/jadedupont/projects/blentAI/llm/projets-hands-on/blentai-llm-cs/tests/test_run_query.py)

Couvre:
- routage `order_help` vers humain sans SQL,
- scénario `order_info` de bout en bout,
- identité invalide,
- blocage d'une requête SQL injectée avant exécution.

## Exécuter les tests
```bash
PYTHONPATH=. pytest -q
```

## Données
- Base SQLite: `orders.db`
- Exports CSV: `users.csv`, `orders.csv`

