Feature: A user enables notifications for a repository

    Scenario: The user navigates to the notifications page

        Given the user is logged in the web interface
        When he clicks in the more button in the repo info box
        And clicks in the settings link
        And clicks in the notifications navigation item
        Then he sees the notifications page

    Scenario: The user enables a notification

        Given the user is in the notifications page
        When he clicks in the cofigure slack notification button
        And fills the webhook URL field
        And clicks in the enable button
        Then he sees the "Slack notification enabled" message

    Scenario: The user disables a notification

        Given the user has enabled the slack notification
        When he clicks in the cofigure slack notification button
        And clicks in the disable button
        Then he sees the "Slack notification disabled" message
