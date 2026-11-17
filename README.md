# Surv_bourse

Agent de surveillance bourse & crypto base sur un workflow Mistral.

Chaque jour, le workflow `market-buffett-scan` :

1. Recupere l'historique hebdomadaire (10 ans) de chaque actif via Yahoo Finance (yfinance).
2. Calcule la moyenne mobile de 200 semaines (MM200 sem.) et detecte les actifs dont le cours est en dessous.
3. Applique les criteres facon Buffett :
   - **Actions** : ROE >= 15%, marge nette >= 10%, dette/fonds propres moderee, croissance des revenus >= 5%, PER raisonnable (<= 25). Un score 0-5 est calcule.
   - **Cryptos** : cours sous la MM200 semaines (zone d'accumulation historique), drawdown eleve par rapport a l'ATH, tendance long terme (MM200 sem. ascendante).
4. Envoie un e-mail (via Resend) listant les actifs qui combinent un cours sous la MM200 semaines et des fondamentaux solides — c'est-a-dire des actifs qui ont "toutes les raisons de remonter".

## Liste des actifs

Par defaut : 12 grandes actions americaines (AAPL, MSFT, GOOGL, AMZN, BRK-B, JNJ, KO, PG, UNH, COST, WM, XOM),
le CAC 40, les grandes valeurs du SBF 120 (ADP, Eurofins, Getlink, Rexel, Unibail, Klepierre, Fnac Darty, Ayvens, Soitec, Ubisoft),
les principales blue chips europeennes eligibles au PEA (ASML, Adyen, Unilever, ING, Philips, Heineken, SAP, Siemens, Allianz, Bayer, BMW, Mercedes, Deutsche Telekom, Merck, Novo Nordisk, Intesa, Enel, ENI, Generali, Santander, Inditex, Iberdrola, Cellnex ; hors Suisse et Royaume-Uni, non eligibles au PEA),
plus BTC-USD et ETH-USD.
Modifiable dans l'input du workflow (`stocks`, `cryptos`) sans toucher au code.

## Configuration

Variables d'environnement du worker (secrets du workspace Mistral) :

| Variable | Description |
|---|---|
| `RESEND_API_KEY` | Cle API Resend pour l'envoi des e-mails |
| `RESEND_FROM_EMAIL` | Adresse expediteur verifiee chez Resend (defaut : `onboarding@resend.dev`) |

Le destinataire par defaut est `quemenerm1@gmail.com` (modifiable via l'input `recipient_email`).

## Test local

```bash
cd apps/worker
uv sync
uv run pytest
```

## Cas d'usage

- Execution manuelle : lancer `market-buffett-scan` depuis Mistral Studio.
- Execution planifiee : un schedule quotidien declenche le workflow sur le deployment gere.

> Cette analyse automatique ne constitue pas un conseil en investissement.
