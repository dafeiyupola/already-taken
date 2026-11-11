"""The whole point of this tool is one function, so that is what gets tested."""

from already_taken import FREE, TAKEN, UNSURE, classify


def test_nothing_anywhere_is_free():
    assert classify([], [])[0] == FREE


def test_an_open_pull_request_takes_it():
    state, why = classify([("pull", "#12 fix it", "open", True)], [])
    assert state == TAKEN
    assert "open PR" in why


def test_a_merged_pull_request_takes_it_even_if_the_issue_is_still_open():
    # The issue outlives the PR until something closes it, so "open issue" proves nothing.
    assert classify([("pull", "#12 fix it", "merged", True)], [])[0] == TAKEN


def test_a_commit_that_mentions_the_issue_takes_it():
    assert classify([("commit", "abc1234 fixes it", "commit", False)], [])[0] == TAKEN


def test_a_closed_unmerged_pull_request_is_not_taken_but_worth_a_look():
    # Someone tried and gave up. The issue is still anyone's, but their notes may say why.
    state, why = classify([("pull", "#12 abandoned", "closed", False)], [])
    assert state == UNSURE
    assert "abandoned" in why


def test_a_touched_file_makes_it_unsure_rather_than_free():
    # The case this tool was written for: no reference anywhere, but the file moved.
    state, why = classify([], [("scripts/x.py", "deadbee", "unrelated sweep")])
    assert state == UNSURE
    assert "scripts/x.py" in why


def test_an_open_pr_outranks_a_touched_file():
    state, _ = classify([("pull", "#12 fix it", "open", True)], [("a.py", "deadbee", "x")])
    assert state == TAKEN


def test_a_closed_issue_is_taken_even_with_no_reference():
    # Closed means someone settled it. Reporting FREE sends the reader to a dead issue.
    state, why = classify([], [], closed=True)
    assert state == TAKEN
    assert "closed" in why


def test_closed_outranks_a_touched_file():
    assert classify([], [("a.py", "deadbee", "x")], closed=True)[0] == TAKEN


def test_free_says_so_when_the_issue_names_no_file():
    # Two different facts: "the files it names are untouched" and "it names no
    # files, so that check never ran". Only one of them is reassuring.
    state, why = classify([], [], files_named=0)
    assert state == FREE
    assert "could not be ruled out" in why


def test_free_is_plain_when_a_file_was_actually_checked():
    state, why = classify([], [], files_named=1)
    assert state == FREE
    assert "untouched" in why


def test_a_cross_reference_without_closing_syntax_is_not_taken():
    # The flisk case: PR #3850 says "Fixes #3829" and merely mentions #3852 on the way.
    state, why = classify([("pull", "#3850 other fix", "merged", False)], [])
    assert state == UNSURE
    assert "never claimed closed" in why


def test_a_closing_pull_request_still_takes_it():
    assert classify([("pull", "#3850 fixes this", "merged", True)], [])[0] == TAKEN
