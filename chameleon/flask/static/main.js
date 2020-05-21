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

function onSubmit() {
    if (!taglist_field.options.length) {
        return false
    }
    for (var x = 0; x < taglist_field.options.length; i++) {
        taglist_field.options[x].selected = true;
    }
    return true;
}