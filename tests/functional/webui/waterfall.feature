Feature:
    A user trigger builds and watches it in the waterfall.

    Scenario: A user see buildsets in the waterfall
        Given the user is logged in the web interface
        When he clicks in the waterfall button
        Then he sees a list of builds in the waterfall

    # NOTE: The tests commented here are commented because the
    # ui is buggy. A new one will be written.

    # Scenario: A user sees builds running
    #     Given the user is already in the waterfall
    #     When he sees the builds running
    #     Then he waits for all builds to complete

    Scenario: A user inspects the buildset details
        Given the user is already in the waterfall
        When he clicks in the buildset details button
        Then he sees the buildset details modal
        And closes the details modal

    # Scenario: A user inspects the step details
    #     Given the user is already in the waterfall
    #     When he clicks in the step details button
    #     Then he sees the step details modal
    #     And closes the details modal

    Scenario: A user cancels a build
        Given the user is already in the waterfall
        When he clicks in the reschedule build button
        And cancels the newly added build
        Then he sees the build cancelled
