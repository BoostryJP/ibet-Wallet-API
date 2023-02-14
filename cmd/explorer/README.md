# ibet-Wallet-API BC-Explorer

## Run

### with container

```bash
> docker exec -it ibet-wallet-api bash --login
> apl@2e5a80e06fcb:/$ ibet-explorer

 Usage: ibet-explorer [OPTIONS] [URL]

╭─ Arguments ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│   url      [URL]  ibet-Wallet-API server URL to connect [default: http://localhost:5000]                                                                                                                                                                                   │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --install-completion          Install completion for the current shell.                                                                                                                                                                                                    │
│ --show-completion             Show completion for the current shell, to copy it or customize the installation.                                                                                                                                                             │
│ --help                        Show this message and exit.                                                                                                                                                                                                                  │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

- **URL**: ibet-Wallet-API URL.
- You can run this on pythonic way in local.

### Poetry
```bash
> poetry install
> poetry run python src/main.py --url http://localhost:5000
```

### Pip
```bash
> pip install -e ./
> python src/main.py --url http://localhost:5000
```

## Screenshots 👀

![block](https://user-images.githubusercontent.com/15183665/218406188-345a28a2-15da-41d4-b606-808d541ca09a.png)

![transaction](https://user-images.githubusercontent.com/15183665/218406277-05eaa4c9-9433-42a8-8cc4-08d83a003f64.png)

