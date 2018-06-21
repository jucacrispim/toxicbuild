Feature:

    A user imports repositories from github

    Scenario:

        The user redirected from the github installation page and sees
        his repositories imported

        Given the user is sent to the setup url by github
        When he is redirected to the login page
        And he inserts "someguy" as user name
        And inserts "123" as password
        And clicks in the login button
        Then he sees the main page
        And his repositories beeing imported from github
