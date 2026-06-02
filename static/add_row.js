// ============================================================
// add_row.js
//
// Powers the "+ Add another event" button on the quadrant forms.
//
// What it does, in plain English:
//   When the user clicks "Add another event", we clone the first
//   event row, clear its values, and append it to the form. This
//   lets the user enter as many events as they want without the
//   page reloading.
//
// Why this is safe:
//   - It only manipulates the DOM (the page structure in the
//     browser). It sends nothing anywhere on its own.
//   - The cloned rows reuse the same field names (title, day,
//     start, end), which Flask reads as parallel arrays on submit.
//   - All real validation happens SERVER-SIDE. This script is a
//     convenience only; it can't bypass any security checks.
//
// No external libraries. Plain browser JavaScript.
// ============================================================

// Wait until the page's HTML is fully loaded before wiring up the
// button. Otherwise the elements we're looking for might not exist yet.
document.addEventListener("DOMContentLoaded", function () {

  var addButton = document.getElementById("add-row-btn");
  var rowsContainer = document.getElementById("event-rows");

  // Defensive: if either element is missing (e.g. on a page that
  // doesn't have the form), do nothing rather than throwing an error.
  if (!addButton || !rowsContainer) {
    return;
  }

  addButton.addEventListener("click", function () {
    // Find the existing rows. We clone the FIRST one as our template
    // because we know it always exists (the server renders one row).
    var existingRows = rowsContainer.getElementsByClassName("event-row");
    if (existingRows.length === 0) {
      return;
    }

    var templateRow = existingRows[0];

    // cloneNode(true) makes a deep copy, including the inputs/select.
    var newRow = templateRow.cloneNode(true);

    // Clear the values in the cloned row so the user starts fresh.
    // We loop over every input and select inside the new row.
    var inputs = newRow.querySelectorAll("input");
    for (var i = 0; i < inputs.length; i++) {
      inputs[i].value = "";
    }
    var selects = newRow.querySelectorAll("select");
    for (var j = 0; j < selects.length; j++) {
      selects[j].selectedIndex = 0; // reset dropdown to the "-- day --" option
    }

    // Add the fresh row to the bottom of the container.
    rowsContainer.appendChild(newRow);
  });
});
