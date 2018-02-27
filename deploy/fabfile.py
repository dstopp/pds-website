from __future__ import print_function
import sys
import socket
import time
from fabric.api import env, lcd, run, abort, local
from fabric.contrib.console import confirm
from secrets import PROD_DIR
import getpass
"""
    This must be run on the admin server.

    Run like so:

        fab deploy admin

        fab deploy production

    * The reason this is run on admin is people work on different
    local dev environments and it was getting tedious maintaining this
    fabfile working on Windows machines.

"""
# config
admin_website =  'https://admin.pds-rings.csc.seti.org'

REPO = 'https://github.com/SETI/pds-website.git'
branch = 'deploy_redux'
git_revision = ''  # use this to roll back to past commit, leave blank for latest
jekyll_version = '_3.4.4_' # leave blank to go with admin server system default

prod_host = 'server2.pds-rings.seti.org'
prod_website = 'https://{}'.format(prod_host)
env.hosts = [prod_host]

# a home directory location for the repo on admin and production
# don't forget trailing slashes here:
admin_repo = '~/ringsnode_website/'  # your copy of the repo on admin server home dir
                                    # this script deploys the website
                                    # generated by this install either
                                    # to admin or to production web roots
                                    # but first it builds it here
                                    # in admin_repo in home dir

prod_staging_dir = '~/website_staging/'  # an rsync target on the production machine
                                         # since you can't rsync directly into
                                         # prod web root from another machine

PROD_USR = getpass.getuser()  # expects same user name on all machines
                              # = local, admin, prod

prod_login = '{}@{}'.format(PROD_USR, prod_host)
prod_staging_path = '{}@{}:{}'.format(PROD_USR, prod_host, prod_staging_dir)


def deploy():
    """ do some setup things """
    pass  # just kidding there are no setup things


def admin():
    """ This script will update a local repo in user home directory
        to the branch and git_revision on github,
        build the site in user local directory, then
        deploy the website to admin server web root.
        You must be logged into admin running this script on admin.
    """
    # get the latest from github
    with lcd(admin_repo):
        local('git checkout {}'.format(branch))
        if git_revision:
            local('git checkout {}'.format(git_revision))
        local('git pull')

    # build the site and then move into web root
    with lcd(admin_repo + "website/"):

        local("jekyll {} build --config _config.yml,_config.production.yml".format(jekyll_version))

        # copy the website to the production directory
        rsync_cmd = "sudo rsync -r %s --exclude=*.tif --exclude=*.tiff --exclude=*.tgz --exclude=*.tar.gz _site/ %s. "

        # first do a dry run:
        local(rsync_cmd % ('--dry-run --itemize-changes ',PROD_DIR))
        if confirm("The above was a dry run. If the above looks good, push to admin site:"):
            local(rsync_cmd % ('',PROD_DIR))
            print("\n*** Admin Website Has Been Updated! ***\n Take a look: {}".format(admin_website))
            sys.exit()
        else:
            print("\nDeployment Aborted\n")


def production():
    """ rsyncs admin server from admin_repo to production server web root
    """
    if confirm("""
            -----

            You will be deploying the website from the admin server
            generated in {}
            to the production website at pds-rings.seti.org.

            During this process you will be prompted for a password, where
            you will need to enter your production server sudo password.

            Do you want to continue?

            """.format(admin_repo, default=False)):

        with lcd(admin_repo + "website/"):

            rsync_cmd = "rsync -r {} --exclude=*.tif --exclude=*.tiff --exclude=*.tgz --exclude=*.tar.gz _site/ {}. "

            # move the site over to the production server staging directory
            # this step is here bc server settings = you can't deploy remotely
            # directly into web root
            local(rsync_cmd.format('', prod_staging_path))

            # shell into production, rsync from home dir staging into web root
            local('ssh -t {} "sudo rsync -r {} {}."'.format(prod_login, prod_staging_dir, PROD_DIR))

            print("\n*** Admin Website Has Been Updated! ***\n Take a look: \n https://pds-rings.seti.org")
