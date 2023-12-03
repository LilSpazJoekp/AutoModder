AutoModder
==========

Quick Start
-----------

You will need to do the following before you start.

1. Clone the repository.
2. Fill in the Reddit oauth credentials into the praw.ini file. `Follow this guide to
   get the credentials
   <https://praw.readthedocs.io/en/latest/getting_started/authentication.html>`_
3. Follow the instructions in `this guide
   <https://docs.gspread.org/en/latest/oauth2.html>`_ for the google sheets writer.
4. Run the following command in the root of the project to install the dependencies.

   .. code-block:: shell

       pip install .

5. See the help menu for the commands.

   .. code-block:: shell

       automodder --help

Features
--------

- Modqueue management
      - Bulk removal of posts and comments based on given criteria
- Modmail management
      - Bulk archival of modmail based on given criteria
- Reddit moderator activity stat collector
      - Collects moderator activity stats and prints them to the console or writes them
        to a google sheet
