Feature:

    A user imports repositories from GitLab

    Scenario:

        A user goes to gitlab to import his repositories

        Given the user is logged in the web interface
        When he goes to the repository settings interface
        And clicks in the gitlab import repos button
        Then he is sent to the gitlab login page

    Scenario:

        A user logs in gitlab

        Given the user is in the gitlab login page
        When he fills the gitlab username field
        And fills the gitlab password field
        And clicks in the accept cookies button
        And clicks in the gitlab login button
        Then he sees the main page
        And his repositories beeing imported from gitlab

    #     Then he sees the gitlab authorize page

    # Scenario:

    #     A user authorize the application on gitlab

    #     Given the user is in the gitlab authorization page
    #     When he clicks in the authorize button
    #     Then he sees the main page
    #     And his repositories beeing imported from gitlab
