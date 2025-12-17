# List of Environment Variables

The list of environment variables that can be set for this system is as follows.

## Basic Settings
| Variable Name           | Required | Details                                  | Example                                         | Default                                                   |
|-------------------------|----------|------------------------------------------|-------------------------------------------------|-----------------------------------------------------------|
| APP_ENV                 | False    | Running environment                      | local / dev / live                              | local                                                     |
| NETWORK                 | False    | Running network                          | IBET / IBETFIN                                  | IBET                                                      |
| WEB3_CHAINID            | False    | Blockchain network ID                    | 1010032                                         | IBET: 1500002, IBETFIN: 1010032                           |
| WEB3_HTTP_PROVIDER      | False    | Web3 provider                            | http://localhost:8545                           | http://localhost:8545                                     |
| COMPANY_LIST_URL        | True     | Company list URL                         | https://dummy-company-list.boostry.co.jp        | --                                                        |
| COMPANY_LIST_LOCAL_MODE | False    | Using the local mode of the company list | 0 (not using) / 1 (using)                       | 0                                                         |
| TOKEN_LIST_URL          | True     | Token list URL                           | https://dummy-token-list.boostry.co.jp          | --                                                        |
| PUBLIC_ACCOUNT_LIST_URL | True     | Public account list URL                  | https://dummy-public-account-list.boostry.co.jp | --                                                        |
| DATABASE_URL            | False    | Database URL                             | postgresql://xxxx:xxxx@yyyy:5432/zzzz           | postgresql://ethuser:ethpass@localhost:5432/ethcache      |
| TEST_DATABASE_URL       | False    | Test database URL (for development use)  | postgresql://xxxx:xxxx@yyyy:5432/zzzz           | postgresql://ethuser:ethpass@localhost:5432/ethcache_test |
| APP_LOGFILE             | False    | Output location for application logs     | /some/directory                                 | /dev/stdout (standard output)                             |
| ACCESS_LOGFILE          | False    | Output location for access logs          | /some/directory                                 | /dev/stdout (standard output)                             |
| TZ                      | False    | Time Zone                                | Europe/Berlin                                   | Asia/Tokyo                                                |
| DEFAULT_CURRENCY        | False    | Default currency code                    | EUR                                             | JPY                                                       |


## API Server Settings
The API server uses [Gunicorn](https://docs.gunicorn.org/) as the HTTP server.
The following parameters can be set as environment variables as startup parameters for Gunicorn.

See [Gunicorn's official documentation](https://docs.gunicorn.org/en/stable/run.html#commonly-used-arguments) for details.

| Variable Name              | Required | Details                                                                  | Default |
|----------------------------|----------|--------------------------------------------------------------------------|---------|
| WORKER_COUNT               | False    | The number of worker processes.                                          | 2       |
| WORKER_TIMEOUT             | False    | Workers silent for more than this many seconds are killed and restarted. | 60      |
| WORKER_MAX_REQUESTS        | False    | The maximum number of requests a worker will process before restarting.  | 0       |
| WORKER_MAX_REQUESTS_JITTER | False    | The maximum jitter to add to the max_requests setting.                   | 0       |
| KEEP_ALIVE                 | False    | The number of seconds to wait for requests on a Keep-Alive connection.   | 2       |

## Settings for each use case

### Token
| Variable Name                  | Required | Details                                                            | Example                                    | Default |
|--------------------------------|----------|--------------------------------------------------------------------|--------------------------------------------|---------|
| BOND_TOKEN_ENABLED             | False    | Using ibet Bond token (security token)                             | 0 (not using) / 1 (using)                  | 0       |
| SHARE_TOKEN_ENABLED            | False    | Using ibet Share token (security token)                            | 0 (not using) / 1 (using)                  | 0       |
| MEMBERSHIP_TOKEN_ENABLED       | False    | Using ibet Membership token                                        | 0 (not using) / 1 (using)                  | 0       |
| COUPON_TOKEN_ENABLED           | False    | Using ibet Coupon token                                            | 0 (not using) / 1 (using)                  | 0       |
| TOKEN_LIST_CONTRACT_ADDRESS    | True     | TokenList contract address                                         | 0x0000000000000000000000000000000000000000 | --      |
| PERSONAL_INFO_CONTRACT_ADDRESS | True*    | PersonalInfo contract address (*Set if you enable security tokens) | 0x0000000000000000000000000000000000000000 | --      |
| TOKEN_NOTIFICATION_ENABLED     | True*    | Use of token-related notification (*Set if you enable tokens)      | 0 (not using) / 1 (using)                  | --      |
| TOKEN_CACHE                    | False    | Enable cache storage of token attribute data                       | 0 (not using) / 1 (using)                  | 1       |
| TOKEN_CACHE_TTL                | False    | Token attribute data cache expiration time (seconds)               | 36000                                      | 43200   |
| TOKEN_SHORT_TERM_CACHE_TTL     | False    | Token attribute data cache (Short-Term) expiration time (seconds)  | 60                                         | 40      |

### Token Escrow
| Variable Name                               | Required | Details                                     | Example                                    | Default |
|---------------------------------------------|----------|---------------------------------------------|--------------------------------------------|---------|
| IBET_ESCROW_CONTRACT_ADDRESS                | False    | Ibet Escrow contract address                | 0x0000000000000000000000000000000000000000 | --      |
| IBET_SECURITY_TOKEN_ESCROW_CONTRACT_ADDRESS | False    | Ibet Security Token Escrow contract address | 0x0000000000000000000000000000000000000000 | --      |

### Token DVP

| Variable Name                               | Required | Details                                     | Example                                    | Default |
|---------------------------------------------|----------|---------------------------------------------|--------------------------------------------|---------|
| IBET_SECURITY_TOKEN_DVP_CONTRACT_ADDRESS    | False    | Ibet Security Token DVP contract address    | 0x0000000000000000000000000000000000000000 | --      |

### On-chain Exchange (Only for utility tokens)
| Variable Name                               | Required | Details                                                                  | Example                                    | Default |
|---------------------------------------------|----------|--------------------------------------------------------------------------|--------------------------------------------|---------|
| PAYMENT_GATEWAY_CONTRACT_ADDRESS            | False    | PaymentGateway contract address                                          | 0x0000000000000000000000000000000000000000 | --      |
| IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS   | False    | IbetExchange contract address for Membership tokens                      | 0x0000000000000000000000000000000000000000 | --      |
| IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS       | False    | IbetExchange contract address for Coupon tokens                          | 0x0000000000000000000000000000000000000000 | --      |
| EXCHANGE_NOTIFICATION_ENABLED               | True*    | Use of exchange-related notification (*Set only if you use IbetExchange) | 0 (not using) / 1 (using)                  | --      |

### Blockchain Explorer
| Variable Name       | Required | Details                                             | Example                   | Default |
|---------------------|----------|-----------------------------------------------------|---------------------------|---------|
| BC_EXPLORER_ENABLED | False    | Parameter for starting the Blockchain Explorer      | 0 (not using) / 1 (using) | 0       |

### Email
Common

| Variable Name                   | Required | Details                                    | Example                         | Default |
|---------------------------------|----------|--------------------------------------------|---------------------------------|---------|
| SMTP_METHOD                     | False    | Email sending method                       | 0:SMTP server, 1:Amazon SES     | 0       |
| SMTP_AUTH_METHOD                | False    | Authentication method                      | 0:PASSWORD, 1:XOAUTH2           | 0       |
| SMTP_SENDER_NAME                | False    | Sender name                                |                                 | --      |
| SMTP_SENDER_EMAIL               | False    | Sender email address                       | example@example.com             | --      |

SMTP server

| Variable Name                 | Required | Details                                   | Example                         | Default |
|-------------------------------|----------|-------------------------------------------|---------------------------------|---------|
| SMTP_SERVER_HOST              | False    | SMTP server name                          | smtp.office365.com              | --      |
| SMTP_SERVER_PORT              | False    | SMTP server port                          | 587                             | --      |
| SMTP_SERVER_ENCRYPTION_METHOD | False    | SMTP server connection encryption method  | 0:STARTTLS, 1:SSL, 2:NO-ENCRYPT | 0       |
| SMTP_SENDER_PASSWORD          | False    | Sender email password                     | (Only if needed)                | --      |

Amazon SES

| Variable Name       | Required | Details         | Example   | Default |
|---------------------|----------|-----------------|-----------|---------|
| AWS_SES_REGION_NAME | False    | AWS region name | us-east-1 | --      |

SMTP XOAUTH2 (Microsoft)

| Variable Name         | Required | Details                 | Example | Default |
|-----------------------|----------|-------------------------|---------|---------|
| SMTP_MS_TENANT_ID     | True     | Microsoft Entra ID (Azure AD) Tenant ID             |         | --      |
| SMTP_MS_CLIENT_ID     | True     | Microsoft Entra ID (Azure AD) Client ID             |         | --      |
| SMTP_MS_CLIENT_SECRET | True*    | Microsoft Entra ID (Azure AD) Client Secret (*Required if Client Certificate is unused) |         | --      |

Send settings

| Variable Name                              | Required | Details                                                                         | Example                       | Default |
|--------------------------------------------|----------|---------------------------------------------------------------------------------|-------------------------------|---------|
| ALLOWED_EMAIL_DESTINATION_DOMAIN_LIST      | False    | Domains allowed to send email. Not set if all domains are allowed.              | example.com,example.net       | --      |
| DISALLOWED_DESTINATION_EMAIL_ADDRESS_REGEX | False    | Regular expression for destination email addresses that are not allowed to send | ^[a-zA-Z0-9_.+-]+@example.com | --      |




### Chat Webhook
| Variable Name     | Required | Details          | Example                                                                        | Default |
|-------------------|----------|------------------|--------------------------------------------------------------------------------|---------|
| CHAT_WEBHOOK_URL  | False    | Chat webhook url | https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX  | --      |


## Appendix

### Email Configuration Matrix

| Variable / Pattern | SMTP Password | SMTP XOAUTH2 | Amazon SES | Details |
| :--- | :---: | :---: | :---: | :--- |
| **BASE SETTINGS** | | | | |
| `SMTP_METHOD` | `0` | `0` | `1` | 0:SMTP, 1:SES |
| `SMTP_SENDER_EMAIL` | Required | Required | Required | Sender definition |
| `SMTP_SENDER_NAME` | Optional | Optional | Optional | Sender display name |
| **SMTP AUTH** | | | | |
| `SMTP_AUTH_METHOD` | `0` | `1` | - | 0:Password, 1:XOAUTH2 |
| **SMTP SERVER** | | | | |
| `SMTP_SERVER_HOST` | Required | Required | - | e.g. smtp.office365.com |
| `SMTP_SERVER_PORT` | Required | Required | - | e.g. 587 |
| `SMTP_SERVER_ENCRYPTION_METHOD`| Optional | Optional | - | 0:STARTTLS (Default), 1:SSL, 2:None |
| `SMTP_SENDER_PASSWORD` | Required | - | - | For SMTP Auth |
| **MICROSOFT OAUTH** | | | | |
| `SMTP_MS_TENANT_ID` | - | Required | - | |
| `SMTP_MS_CLIENT_ID` | - | Required | - | |
| `SMTP_MS_CLIENT_SECRET` | - | Required | - | |
| **AMAZON SES** | | | | |
| `AWS_SES_REGION_NAME` | - | - | Required | |
