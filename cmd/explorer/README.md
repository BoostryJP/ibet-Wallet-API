# ibet-Wallet-API BC-Explorer

## Setup

### Poetry
```bash
poetry install
```

### Pip
```bash
pip install -e ./
```

## Run

```bash
> ibet-explorer --help

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

- You can run this on pythonic way.

### Poetry
```bash
poetry run python src/main.py --url http://localhost:5000
```

### Pip
```bash
python src/main.py --url http://localhost:5000
```

## Screenshots 👀

![block](https://user-images.githubusercontent.com/15183665/218406188-345a28a2-15da-41d4-b606-808d541ca09a.png)

![transaction](https://user-images.githubusercontent.com/15183665/218406277-05eaa4c9-9433-42a8-8cc4-08d83a003f64.png)

