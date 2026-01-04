let searchtype = "set"
document.addEventListener("DOMContentLoaded", function () {
    // Ensure initial state when the page loads
    document.getElementById("setSearchList")?.classList.remove("d-none");
    document.getElementById("queryYear")?.classList.remove("d-none");
    document.getElementById("subsetSearchList")?.classList.remove("d-none");
    document.getElementById("playerSearchList")?.classList.add("d-none");
    document.getElementById("boxSearchList")?.classList.add("d-none");
    const toggleButton = document.getElementById("toggleSearchButton");
    if (toggleButton) toggleButton.textContent = "Search: Set";
});
function toggleSetPlayerBox() {
    const sections = [
    { id: "setSearchList", label: "Set" },
    { id: "playerSearchList", label: "Player" },
    { id: "boxSearchList", label: "Box" }
    ];

    const toggleButton = document.getElementById("toggleSearchButton");
    const queryYear = document.getElementById("queryYear");
    const subsetSearchList = document.getElementById("subsetSearchList");
    const qty = document.getElementById("qty");

    // Find which section is currently visible
    const visibleIndex = sections.findIndex(
    s => !document.getElementById(s.id).classList.contains("d-none")
    );

    // Hide all sections
    sections.forEach(s => document.getElementById(s.id).classList.add("d-none"));

    // Determine the next section to show
    const nextIndex = (visibleIndex + 1) % sections.length;
    const nextSection = sections[nextIndex];

    // Show next section
    document.getElementById(nextSection.id).classList.remove("d-none");

    // Update button text and global search type
    if (toggleButton) {
        toggleButton.textContent = `Search: ${nextSection.label}`;
        searchtype = nextSection.label.toLowerCase();
        console.log("Search type set to:", searchtype);
    }

    // Handle Set search grouping
    if (nextSection.id === "setSearchList") {
        queryYear?.classList.remove("d-none");
        subsetSearchList?.classList.remove("d-none");
    } else {
        queryYear?.classList.add("d-none");
        subsetSearchList?.classList.add("d-none");
    }

    // Reset irrelevant fields when switching search types
    // (clears stale values from previous search modes)
    document.getElementById("setSearchList").value = "";
    document.getElementById("subsetSearchList").value = "";
    document.getElementById("queryYear").value = "";
    document.getElementById("boxSearchList").value = "";
    document.getElementById("playerSearchList").value = "";
    qty.value = "0";

    console.log("Cleared previous search inputs.");
}

function tableFilterFunction() {
    // https://www.w3schools.com/howto/howto_js_filter_table.asp
    // https://stackoverflow.com/a/1085810
    // Declare variables
    var input, filter, table, tr, td, i, txtValue, columnSelect;
    columns = document.getElementById("tableFilterSelect");
    columnSelect = columns.value;
    input = document.getElementById("tableFilter");
    filter = input.value.toUpperCase();
    table = document.getElementById("itemsTable");
    tr = table.getElementsByTagName("tr");
    searchCounter = 0;
    // Loop through all table rows, and hide those who don't match the search query
    for (i = 1; i < tr.length; i++) { // starting at 1 to exclude header
    td = tr[i].getElementsByClassName(columnSelect)[0];
    if (td) {
        txtValue = td.textContent || td.innerText;
        if (txtValue.toUpperCase().indexOf(filter) > -1) {
        tr[i].style.display = "";
        searchCounter++;
        } else {
        tr[i].style.display = "none";
        }
    }
    }
    document.getElementById('num-results').innerHTML = searchCounter;
}