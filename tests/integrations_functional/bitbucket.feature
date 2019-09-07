Feature:

    A user imports repositories from BitBucket

    Scenario:

        A user goes to bitbucket to import his repositories

        Given the user is logged in the web interface
        When he goes to the repository settings interface
        And clicks in the bitbucket import repos button
        Then he is sent to the bitbucket login page

    Scenario:

        A user logs in bitbucket

        Given the user is in the bitbucket login page
        When he fills the bitbucket username field
        And fills the bitbucket password field
        And clicks in the bitbucket login button
        Then he sees the main page
        And his repositories beeing imported from bitbucket

    #     Then he sees the bitbucket authorize page

    # Scenario:

    #     A user authorize the application on bitbucket

    #     Given the user is in the bitbucket authorization page
    #     When he clicks in the authorize button
    #     Then he sees the main page
    #     And his repositories beeing imported from bitbucket
