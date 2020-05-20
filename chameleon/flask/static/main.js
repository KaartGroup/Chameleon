var tagentry_field;
var taglist_field;

function main() {
    tagentry_field = document.getElementById("tagentry_id");
    taglist_field = document.getElementById("taglist");
}

function addToList() {
    var option = document.createElement("option");
    var tag = tagentry_field.value.trim();
    tagentry_field.value = "";
    if (!tag) {
        return;
    }
    option.text = tag;
    taglist_field.add(option);
}

function selectAllOptions() {
    for (x in taglist_field.options) {
        x.selected = true;
    }
    return true;
}