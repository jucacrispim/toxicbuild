Feature: A user trigger builds and watches it in the waterfall.

    Scenario: A user see buildsets in the waterfall
        Given the user is logged in the web interface
        When he clicks in the waterfall button
        Then he sees a list of builds in the waterfall

    Scenario: The user filters by branch
        Given the user is already in the waterfall
        When he clicks in the branch select filter
        And clicks in the master branch
        Then he sees a list of builds in the waterfall

    Scenario: The user reschedules a buildset
        Given the user is already in the waterfall
        When he clicks in the reschedule buildset button
        Then he sees the "Buildset re-scheduled" message

    Scenario: The user waits for the builds to complete
        Given already rescheduled a buildset
        When The builds start running
        Then he waits for the builds complete
