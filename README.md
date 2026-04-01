# LLM SQL Bot - Service Client E-commerce

## Objectif
Ce projet implémente un assistant capable de répondre à des questions sur des commandes clients à partir d'une base SQLite (`data/orders.db`), avec des garde-fous de sécurité.

Le flux principal est dans [llm-sql.ipynb](./llm-sql.ipynb).

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
La fonction [helpers/security.py](./helpers/security.py) applique notamment:
- rejet si la requête n'est pas un `SELECT`.
- rejet si `WHERE` absent.
- rejet de patterns à risque (`OR`, `UNION`, `--`, `/* */`, `;`).
- obligation de présence de `user_id = <authenticated_user_id>`.
- rejet si un autre `user_id` apparaît dans la clause `WHERE`.

## Tests
### 1. Tests unitaires sécurité
Fichier: [tests/test_security.py](./tests/test_security.py)

Couvre:
- cas valides (`user_id` simple et avec alias),
- erreurs de filtre (`WHERE` absent, mauvais `user_id`),
- tentatives d'injection (`OR`, `UNION`, commentaires, multi-statements).

### 2. Tests unitaires routage
Fichier: [tests/test_query_routing.py](./tests/test_query_routing.py)

Couvre:
- choix de la meilleure route lorsque le score est clair,
- rejet en `out_of_scope` lorsque le score est trop faible,
- rejet en `out_of_scope` lorsque la classification est ambiguë,
- calcul des scores à partir d'un encodeur et d'une fonction de similarité.

### 3. Tests unitaires règles métier
Fichier: [tests/test_business_rules.py](./tests/test_business_rules.py)

Couvre:
- enrichissement des requêtes SQL avec les colonnes nécessaires à la réponse métier,
- normalisation de filtres de statut invalides générés par le LLM,
- réponses forcées pour les cas livraison, paiement et statut de commande,
- gestion des informations de livraison incomplètes.

### 4. Tests d'intégration du flux
Fichier: [tests/test_run_query.py](./tests/test_run_query.py)

Couvre:
- routage `order_help` vers humain sans SQL,
- scénario `order_info` du pipeline orchestré avec composants mockés,
- identité invalide,
- blocage d'une requête SQL injectée avant exécution,
- nettoyage d'une requête SQL générée avec point-virgule final,
- retour explicite lorsqu'aucune commande ne correspond à la demande.

Les tests automatisés ne chargent pas les vrais modèles LLM. Le flux réel avec le modèle de génération et le modèle d'embedding est présenté dans le notebook [llm-sql.ipynb](./llm-sql.ipynb).

## Installation
```bash
pip install -r requirements.txt
```

## Exécuter les tests
```bash
PYTHONPATH=. pytest -q
```

## Données (data folder)
- Base SQLite: `data/orders.db`
- Exports CSV: `data/users.csv`, `data/orders.csv`
