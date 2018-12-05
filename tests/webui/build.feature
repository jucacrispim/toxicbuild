Feature: A user sees a build running in the build details page

    Scenario: A user reschedules a buildset
        Given the user is logged in the web interface
        And is in the waterfall
        When he clicks in the reschedule buildset button in the waterfall
        Then he sees the "Buildset re-scheduled" message

    Scenario: A user navigates to the build details page
        Given the user already rescheduled a buildset in the waterfall
        When the user clicks in the build details button
        Then he sees the build details page

    Scenario: The user watches the build in the details page
        Given the user is in the build details page
        Then he waits for the build to finish
