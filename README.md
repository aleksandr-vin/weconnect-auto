# WeConnect Auto(matic)

CLI or Python client for scripting your Volkswagen auto info from https://www.vwbedrijfswagens.nl/.


## Quickstart

Install as *uv tool*:

    uv tool install git+https://github.com/aleksandr-vin/weconnect-auto.git

Login:

    export VW_USERNAME=my@email.home
    export VW_PASSWORD=...password...

    uv run vwcar login

Run:

    uv run vwcar last-shortterm-tripdata
