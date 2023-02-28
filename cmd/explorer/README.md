# ibet-Wallet-API BC-Explorer

## Run

### with container

```bash
> docker exec -it -e "TERM=xterm-256color" ibet-wallet-api bash --login
> apl@2e5a80e06fcb:/$ ibet-explorer

 Usage: ibet-explorer [OPTIONS] [URL] [LOT_SIZE]

╭─ Arguments ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│   url           [URL]       ibet-Wallet-API server URL to connect [default: http://localhost:5000]                                                                                                                                                                         │
│   lot_size      [LOT_SIZE]  Lot size to fetch Block Data list [default: 30]                                                                                                                                                                                                │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --install-completion        [bash|zsh|fish|powershell|pwsh]  Install completion for the specified shell. [default: None]                                                                                                                                                   │
│ --show-completion           [bash|zsh|fish|powershell|pwsh]  Show completion for the specified shell, to copy it or customize the installation. [default: None]                                                                                                            │
│ --help                                                       Show this message and exit.                                                                                                                                                                                   │
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

![query-setting](https://user-images.githubusercontent.com/15183665/221606898-6795e176-b286-42d9-bc81-6b73117cf978.png)

![block](https://user-images.githubusercontent.com/15183665/221606911-fbb9b9ba-97f4-4eb8-9f3e-c8bffc7b18ae.png)

![transaction](https://user-images.githubusercontent.com/15183665/218406277-05eaa4c9-9433-42a8-8cc4-08d83a003f64.png)

