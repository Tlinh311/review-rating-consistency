"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const {
    getStatusView,
    validateReview,
    formatPercent,
} = require("../../static/js/main.js");


test("maps all prediction statuses", () => {
    assert.equal(getStatusView("consistent").label, "Consistent");
    assert.equal(getStatusView("potential_mismatch").label, "Mismatch");
    assert.equal(getStatusView("inconclusive").label, "Inconclusive");
});


test("validates review input", () => {
    assert.equal(validateReview(""), "Please enter the review text.");
    assert.equal(validateReview("good food"), "");
    assert.equal(
        validateReview("a".repeat(5001)),
        "Review text must not exceed 5,000 characters."
    );
});


test("formats percentages", () => {
    assert.equal(formatPercent(63.341, 2), "63.34%");
});
