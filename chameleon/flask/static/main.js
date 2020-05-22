var tagentry_field;
var taglist_field;
var mainform;

window.onload = function() {
    tagentry_field = document.getElementById("tagentry_id");
    taglist_field = document.getElementById("taglist");
    mainform = document.getElementById("mainform")

    onTaglistChange();
    taglist_field.onchange = onTaglistChange;
    mainform.onsubmit = onSubmit;
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
    onTaglistChange();
}

function removeFromList() {
    if (taglist_field.selectedIndex == -1) {
        taglist_field.setCustomValidity("Please select a tag to remove");
        taglist_field.reportValidity();
        tagentry_field.setCustomValidity('');
        return;
    }
    taglist_field.remove(taglist_field.selectedIndex);
}

function clearList() {
    taglist_field.options.length = 0;
}

function onSubmit() {
    for (var x = 0; x < taglist_field.options.length; x++) {
        taglist_field.options[x].selected = true;
    }
}

function onTaglistChange() {
    if (!taglist_field.options.length) {
        taglist_field.setCustomValidity('Please add at least one tag!');
    } else {
        taglist_field.setCustomValidity('');
    }
}