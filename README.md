# 🛡️ LLM SQL Bot – Sécurité & Tests

## 📌 Objectif
Ce projet implémente un bot basé sur un LLM capable de générer des requêtes SQL à partir de questions utilisateur, avec une **protection des données** garantissant que chaque utilisateur ne peut accéder qu'à ses propres commandes.

---

## 🔐 Sécurité mise en place

### ✔️ Isolation des données utilisateur
Chaque requête SQL doit obligatoirement contenir une condition :

```sql
WHERE user_id = <authenticated_user_id>

### Lancer les tests
PYTHONPATH=. pytest