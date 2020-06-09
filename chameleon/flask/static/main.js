var tagEntryField;
var tagListField;
var tagAutocomplete;
var mainform;
var progressbar;
var progressbarLabel;
var addButton;
var removeButton;
var clearButton;
var easyTabDiv;
var easyInputs;
var locationInput;
var startDateInput;
var manualTabDiv;
var manualInputs;
var valueSpan;
var maxSpan;
var filterEntryField;
var filterListField;
var filterAddButton;
var filterRemoveButton;
var filterClearButton;

var evsource;

// EventSource = SSE;

function sendData() {
    const FD = new FormData(mainform);
    evsource = new SSE("/result", {
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
    tagEntryField = document.getElementById("tagentry_id");
    tagListField = document.getElementById("tagList");
    tagAutocomplete = this.document.getElementById("tag_autocomplete");
    mainform = document.getElementById("mainform");

    progressbar = document.getElementById("progressbar");
    progressbarLabel = document.getElementById("progressbarlabel");

    addButton = document.getElementById("add_button");
    removeButton = document.getElementById("remove_button");
    clearButton = document.getElementById("clear_button");

    easyTabDiv = document.getElementById("easytab");
    // easyinputs = easytabdiv.getElementsByTagName("input");

    manualTabDiv = document.getElementById("manualtab");
    manualInputs = manualTabDiv.getElementsByTagName("input");

    locationInput = document.getElementsByName("location")[0];
    startDateInput = document.getElementsByName("startdate")[0];
    filterEntryField = document.getElementById("filterAddField");
    filterListField = document.getElementById("filterList");
    filterAddButton = document.getElementById("filterAddButton");
    filterRemoveButton = document.getElementById("filterRemoveButton");
    filterClearButton = document.getElementById("filterClearButton");

    valueSpan = document.getElementById("curitem");
    maxSpan = document.getElementById("maxitem");

    onTagListChange();
    loadTagAutocomplete();
    onTabChange();
    window.onhashchange = onTabChange;
    tagListField.onchange = onTagListChange;
    addButton.onclick = addToList;
    removeButton.onclick = removeFromList;
    clearButton.onclick = clearList;
    filterAddButton.onclick = addFilter;
    mainform.addEventListener("submit", function(event) {
        event.preventDefault();
        onSubmit();
        sendData();
    });
};

function onTabChange() {
    var isManualTab = window.location.hash == "#manualtab";
    easyTabDiv.disabled = isManualTab;
    manualTabDiv.disabled = !isManualTab;

    // Cleans the URL of unnecessary hash
    if (window.location.hash == "") {
        history.replaceState(null, "", window.location.href.split("#")[0]);
    }
}

function addToList() {
    var option = document.createElement("option");
    var tag = tagEntryField.value.trim();
    tagEntryField.value = "";
    if (!tag) {
        return;
    }
    option.text = tag;
    taglist_field.add(option);
    onTaglistChange();
}

function removeFromList() {
    if (tagListField.selectedIndex == -1) {
        tagListField.setCustomValidity("Please select a tag to remove");
        tagListField.reportValidity();
        tagEntryField.setCustomValidity("");
        return;
    }
    tagListField.remove(tagListField.selectedIndex);
}

function clearList() {
    tagListField.options.length = 0;
}

function onSubmit() {
    for (var x = 0; x < tagListField.options.length; x++) {
        tagListField.options[x].selected = true;
    }
}

function onTagListChange() {
    if (!tagListField.options.length) {
        tagListField.setCustomValidity("Please add at least one tag!");
    } else {
        tagListField.setCustomValidity("");
    }
}

function loadTagAutocomplete() {
    var rawFile = new XMLHttpRequest();
    rawFile.open("GET", "/static/OSMtag.txt", true);
    rawFile.onreadystatechange = function() {
        var arrayOfLines;
        if (
            rawFile.readyState === 4 &&
            (rawFile.status === 200 || rawFile.status == 0)
        ) {
            var alltext = rawFile.responseText;
            arrayOfLines = alltext.split("\n");
            for (var i of arrayOfLines) {
                var option = document.createElement("option");
                option.value = i;
                tagAutocomplete.append(option);
            }
        }
    };
    rawFile.send();
}

function setProgbarMax(event) {
    var max = parseInt(event.data);
    maxSpan.innerText = max;
    progressbar.max = max;
    progressbarLabel.style.display = "block";
}

function setProgbarValue(event) {
    var value = parseInt(event.data);
    valueSpan.innerText = value;
    progressbar.value = value;
    progressbar.innerText =
        "(" + progressbar.value + "/" + progressbar.max + ")";
}

function getFile(event) {
    var path = event.data;
    window.location.pathname = "/download/" + path;
}

function askUserForConfirmation(message) {
    // TODO Finish this function
}

// Copied sse.js code begins here

/**
 * Copyright (C) 2016 Maxime Petazzoni <maxime.petazzoni@bulix.org>.
 * All rights reserved.
 */

var SSE = function(url, options) {
    if (!(this instanceof SSE)) {
        return new SSE(url, options);
    }

    this.INITIALIZING = -1;
    this.CONNECTING = 0;
    this.OPEN = 1;
    this.CLOSED = 2;

    this.url = url;

    options = options || {};
    this.headers = options.headers || {};
    this.payload = options.payload !== undefined ? options.payload : "";
    this.method = options.method || (this.payload && "POST") || "GET";

    this.FIELD_SEPARATOR = ":";
    this.listeners = {};

    this.xhr = null;
    this.readyState = this.INITIALIZING;
    this.progress = 0;
    this.chunk = "";

    this.addEventListener = function(type, listener) {
        if (this.listeners[type] === undefined) {
            this.listeners[type] = [];
        }

        if (this.listeners[type].indexOf(listener) === -1) {
            this.listeners[type].push(listener);
        }
    };

    this.removeEventListener = function(type, listener) {
        if (this.listeners[type] === undefined) {
            return;
        }

        var filtered = [];
        this.listeners[type].forEach(function(element) {
            if (element !== listener) {
                filtered.push(element);
            }
        });
        if (filtered.length === 0) {
            delete this.listeners[type];
        } else {
            this.listeners[type] = filtered;
        }
    };

    this.dispatchEvent = function(e) {
        if (!e) {
            return true;
        }

        e.source = this;

        var onHandler = "on" + e.type;
        if (this.hasOwnProperty(onHandler)) {
            this[onHandler].call(this, e);
            if (e.defaultPrevented) {
                return false;
            }
        }

        if (this.listeners[e.type]) {
            return this.listeners[e.type].every(function(callback) {
                callback(e);
                return !e.defaultPrevented;
            });
        }

        return true;
    };

    this._setReadyState = function(state) {
        var event = new CustomEvent("readystatechange");
        event.readyState = state;
        this.readyState = state;
        this.dispatchEvent(event);
    };

    this._onStreamFailure = function(e) {
        this.dispatchEvent(new CustomEvent("error"));
        this.close();
    };

    this._onStreamProgress = function(e) {
        if (!this.xhr) {
            return;
        }

        if (this.xhr.status !== 200) {
            this._onStreamFailure(e);
            return;
        }

        if (this.readyState == this.CONNECTING) {
            this.dispatchEvent(new CustomEvent("open"));
            this._setReadyState(this.OPEN);
        }

        var data = this.xhr.responseText.substring(this.progress);
        this.progress += data.length;
        data.split(/(\r\n|\r|\n){2}/g).forEach(
            function(part) {
                if (part.trim().length === 0) {
                    this.dispatchEvent(
                        this._parseEventChunk(this.chunk.trim())
                    );
                    this.chunk = "";
                } else {
                    this.chunk += part;
                }
            }.bind(this)
        );
    };

    this._onStreamLoaded = function(e) {
        this._onStreamProgress(e);

        // Parse the last chunk.
        this.dispatchEvent(this._parseEventChunk(this.chunk));
        this.chunk = "";
    };

    /**
     * Parse a received SSE event chunk into a constructed event object.
     */
    this._parseEventChunk = function(chunk) {
        if (!chunk || chunk.length === 0) {
            return null;
        }

        var e = { id: null, retry: null, data: "", event: "message" };
        chunk.split(/\n|\r\n|\r/).forEach(
            function(line) {
                line = line.trimRight();
                var index = line.indexOf(this.FIELD_SEPARATOR);
                if (index <= 0) {
                    // Line was either empty, or started with a separator and is a comment.
                    // Either way, ignore.
                    return;
                }

                var field = line.substring(0, index);
                if (!(field in e)) {
                    return;
                }

                var value = line.substring(index + 1).trimLeft();
                if (field === "data") {
                    e[field] += value;
                } else {
                    e[field] = value;
                }
            }.bind(this)
        );

        var event = new CustomEvent(e.event);
        event.data = e.data;
        event.id = e.id;
        return event;
    };

    this._checkStreamClosed = function() {
        if (!this.xhr) {
            return;
        }

        if (this.xhr.readyState === XMLHttpRequest.DONE) {
            this._setReadyState(this.CLOSED);
        }
    };

    this.stream = function() {
        this._setReadyState(this.CONNECTING);

        this.xhr = new XMLHttpRequest();
        this.xhr.addEventListener(
            "progress",
            this._onStreamProgress.bind(this)
        );
        this.xhr.addEventListener("load", this._onStreamLoaded.bind(this));
        this.xhr.addEventListener(
            "readystatechange",
            this._checkStreamClosed.bind(this)
        );
        this.xhr.addEventListener("error", this._onStreamFailure.bind(this));
        this.xhr.addEventListener("abort", this._onStreamFailure.bind(this));
        this.xhr.open(this.method, this.url);
        for (var header in this.headers) {
            this.xhr.setRequestHeader(header, this.headers[header]);
        }
        this.xhr.send(this.payload);
    };

    this.close = function() {
        if (this.readyState === this.CLOSED) {
            return;
        }

        this.xhr.abort();
        this.xhr = null;
        this._setReadyState(this.CLOSED);
    };
};

// Export our SSE module for npm.js
if (typeof exports !== "undefined") {
    exports.SSE = SSE;
}