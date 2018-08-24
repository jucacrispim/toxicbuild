Feature:
    A user register himself in the system using the web interface.

    Scenario: The user tries to use a not available username

        Given the user is in the regiter page
        When he inserts the "already-exists" username
        Then he sees the not available info message

    Scenario: The user register himself

        Given: the user is in the register page
        When he inserts the "a-good-username" username
        And the "me@myself.com" email
        And the "mypassowrd" password
        And clicks in the sign in button
        Then he sees the main page
