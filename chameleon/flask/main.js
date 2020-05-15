var tagentry_field = document.getElementById("tagentry_id")
var taglist_field = document.getElementById("taglist")

function addToList() {
    var option = document.createElement("option")
    option.text = tagentry_field.value
    tagentry_field.value = ""
    taglist_field.add(option)
}