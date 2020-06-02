var tagentry_field;
var taglist_field;
var mainform;
var progressbar; // placeholder container for WebSocket messages
var progressbarlabel; // placeholder container for WebSocket messages

var evsource;

// EventSource = SSE;

function sendData() {
    const FD = new FormData(mainform);
    evsource = new SSE("/result/", {
        payload: FD,
    });
    evsource.addEventListener("error", function(m) {
        console.log("error");
    });
    evsource.addEventListener("open", function(m) {
        console.log("SSE connection open");
    });
    evsource.addEventListener("message", function(m) {
        console.log("message " + m.data);
    });
    evsource.addEventListener("max", setProgbarMax);
    evsource.addEventListener("value", setProgbarValue);
    evsource.addEventListener("file", getFile);
    evsource.stream();
}

var messageTable = {
    max: setProgbarMax,
    value: setProgbarValue,
};

window.onload = function() {
    tagentry_field = document.getElementById("tagentry_id");
    taglist_field = document.getElementById("taglist");
    mainform = document.getElementById("mainform");
    progressbar = document.getElementById("progressbar");
    progressbarlabel = document.getElementById("progressbarlabel");

    onTaglistChange();
    taglist_field.onchange = onTaglistChange;
    mainform.addEventListener("submit", function(event) {
        event.preventDefault();
        onSubmit();
        sendData();
    });
};

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
        tagentry_field.setCustomValidity("");
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
        taglist_field.setCustomValidity("Please add at least one tag!");
    } else {
        taglist_field.setCustomValidity("");
    }
}

/*
Schema:
{
    type: "max"|"value"|"confirm",
    value: int
}
*/
function messageHandler(message) {
    var parsed = JSON.parse(message);
    messageTable[parsed.type](parsed.value);
}

function setProgbarMax(event) {
    var max = parseInt(event.data);
    progressbar.max = max;
    progressbarlabel.style.display = "block";
}

function setProgbarValue(event) {
    var value = parseInt(event.data);
    progressbar.value = value;
    progressbar.innerText =
        "(" + progressbar.value + "/" + progressbar.max + ")";
}

function getFile(event) {
    var path = event.data;
    // TODO Finish
}

function askUserForConfirmation(message) {
    // TODO Finish this function
}

}