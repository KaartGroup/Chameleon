var tagListField;
var tagAutocomplete;
var mainform;
var locationInput;
var startDateInput;

var easyTabDiv;
var easyInputs;

var manualTabDiv;
var manualInputs;

var filterListGroup;
var tagListGroup;
var progress;

var evsource;

class ItemList {
    constructor(name, required = false) {
        this.addField = document.getElementById(name + "AddField");
        this.addButton = document.getElementById(name + "AddButton");
        this.removeButton = document.getElementById(name + "RemoveButton");
        this.clearButton = document.getElementById(name + "ClearButton");
        this.theList = document.getElementById(name + "List");
        this.required = required;

        this.addButton.addEventListener("click", (e) => {
            this.addToList();
        });
        this.removeButton.addEventListener("click", (e) => {
            this.removeFromList();
        });
        this.clearButton.addEventListener("click", (e) => {
            this.clearList();
        });
    }
    addToList() {
        var option = document.createElement("option");
        var item = this.addField.value.trim();
        this.addField.value = "";
        if (!item) {
            return;
        }
        option.text = item;
        this.theList.add(option);
        this.onTagListChange();
    }
    removeFromList() {
        if (this.theList.selectedIndex == -1) {
            this.theList.setCustomValidity("Please select a tag to remove");
            this.theList.reportValidity();
            this.theList.setCustomValidity("");
            return;
        }
        this.theList.remove(this.theList.selectedIndex);
        this.onTagListChange();
    }

    clearList() {
        this.theList.options.length = 0;
        this.onTagListChange();
    }
    onTagListChange() {
        if (this.required) {
            if (!this.theList.options.length) {
                this.theList.setCustomValidity("Please add at least one item!");
            } else {
                this.theList.setCustomValidity("");
            }
        }
    }
}

class FilterList extends ItemList {
    constructor(name, required = false) {
        super(name, required);
        this.valueField = document.getElementById(name + "ValueField");
        this.typeArray = document.getElementsByName(name + "TypeBox");
    }
    addToList() {
        var option = document.createElement("option");
        var item = [
            this.addField.value.trim(),
            this.valueField.value.trim().split(/[\s,|]+/),
            Array.from(this.typeArray)
            .filter((a) => a.checked)
            .map((a) => a.value),
        ];
        item = item.filter((x) => x);
        this.addField.value = "";
        this.valueField.value = "";
        if (!item[0]) {
            // if (!item.some((x) => x)) {
            return;
        }
        // option.text = item.join("=");
        var keyvalue = [item[0], item[1].join(",")].filter((x) => x).join("=");
        option.text = keyvalue + " (" + item[2].join("") + ")";
        this.theList.add(option);
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

class Progbar {
    constructor() {
        this.progressbar = document.getElementById("progressbar");
        this.progressbarLabel = document.getElementById("progressbarLabel");
        this.valueSpan = document.getElementById("curItem");
        this.maxSpan = document.getElementById("maxItem");
    }
    setMax(event) {
        var max = event.data;
        this.maxSpan.innerText = max;
        this.progressbar.max = parseInt(max);
        this.progressbarLabel.style.display = "block";
    }
    setValue(event) {
        var value = event.data;
        this.valueSpan.innerText = value;
        this.progressbar.value = parseInt(value);
        this.progressbar.innerText =
            "(" + value + "/" + this.progressbar.max + ")";
    }
}

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
    evsource.addEventListener("max", (e) => {
        progress.setMax(e);
    });
    evsource.addEventListener("value", (e) => {
        progress.setValue(e);
    });
    evsource.addEventListener("file", getFile);
    evsource.stream();
}

window.onload = function() {
    tagAutocomplete = document.getElementById("tagAutocomplete");
    mainform = document.getElementById("mainform");

    easyTabDiv = document.getElementById("easytab");

    manualTabDiv = document.getElementById("manualtab");
    manualInputs = manualTabDiv.getElementsByTagName("input");

    locationInput = document.getElementsByName("location")[0];
    startDateInput = document.getElementsByName("startdate")[0];

    filterListGroup = new FilterList("filter");
    tagListGroup = new ItemList("tag", true);
    progress = new Progbar();

    tagListGroup.onTagListChange();

    loadTagAutocomplete();
    onTabChange();
    window.addEventListener("hashchange", onTabChange);
    mainform.addEventListener("submit", function(event) {
        event.preventDefault();
        onSubmit(filterListGroup);
        onSubmit(tagListGroup);
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

function onSubmit(object) {
    for (var x = 0; x < object.theList.options.length; x++) {
        object.theList.options[x].selected = true;
    }
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