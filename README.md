# nightscout-analysis

Ad hoc (for now) analyses of Nightscout data for personal use


# Development setup

1. Clone this repo.

1. Install/update pyenv and Python 3.9.13 if needed, e.g.:

   ```
   brew update && brew upgrade pyenv
   pyenv install 3.9.13
   ```

   Follow pyenv's instructions for adding to the appropriate rc file, reload the
   shell, and navigate to the project root. The project's `.python-version` file
   specifies the appropriate Python version, which you can confirm using `which python`.

1. Create and activate a virtual environment using `venv`:

   ```commandline
   $ python -m venv nsenv
   ```

1. From within the virtual environment, install dependencies:

   ```commandline
   $ . nsenv/bin/activate
   (nsenv) $ pip install -r requirements.txt
   ```

1. Install pre-commit so that basic formatting will be enforced upon committing to the repo:

   ```commandline
   pre-commit install -t pre-push
   ```

1. Create a `.env` file in the project root with the contents:

   ```commandline
   NIGHTSCOUT_URL=https://<your_nightscout_url>/api/v1/
   ```

1. You should now be able to run:

   ```commandline
   (mmenv) $ python demo.py
   ```

## Heroku deployment notes

* This app is currently deployed via Heroku at https://nightscout-analysis.herokuapp.com/. It would be easy to set up review apps (automatic deployment of PR branches) if helpful in the future.
* Keep the `runtime.txt` and `.python-version` synced; `runtime.txt` is used by Heroku to determine the appropriate Python version.
* Heroku uses the `Procfile` which refers to `server` as defined in `app.py`.
