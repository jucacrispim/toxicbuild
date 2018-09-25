Feature: A user reschedule a buildset and see its details

    Scenario: A user navigates to the buildset list page

        Given the user is logged in the web interface
        When he clicks in the summary link
        Then he sees the buildset list page

    Scenario: A user reschedules a buildset

        Given the user is in the buildset list page
        When he clicks in the reschedule button
        Then he sees the buildset running

    Scenario: A user goes to the buildset details page

        Given the user already rescheduled a buildset
        When he clicks in the buildset details link
        Then he sees the buildset details page
