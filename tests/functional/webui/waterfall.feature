Feature:
    A user trigger builds and watches it in the waterfall.

    Scenario: A user see buildsets in the waterfall
        Given the user is logged in the web interface
        When he clicks in the waterfall button
        Then he sees a list of builds in the waterfall

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
