import { SSE } from "/static/sse.js";

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
    get asArray() {
        return Array.from(this.theList.options).map((x) => x.text);
    }
    addToList() {
        var item = this.addField.value.trim();
        if (!item) {
            return;
        }
        if (
            Array.from(this.theList.options)
                .map((x) => x.text)
                .includes(item)
        ) {
            return;
        }
        var option = document.createElement("option");
        this.addField.value = "";
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
        this._typeArray = document.getElementsByName(name + "TypeBox");
    }
    get typeArray() {
        return Array.from(this._typeArray);
    }
    addToList() {
        var item = [
            this.addField.value.trim(),
            this.valueField.value.trim().split(/[\s,|]+/),
            this.typeArray.filter((a) => a.checked).map((a) => a.value),
        ];
        if (!item[0]) {
            return;
        }
        item = item.filter((x) => x);
        var keyvalue = [item[0], item[1].join(",")].filter((x) => x).join("=");
        this.addField.value = "";
        this.valueField.value = "";
        var option = document.createElement("option");
        var optionstring = keyvalue + " (" + item[2].join("") + ")";
        if (
            Array.from(this.theList.options)
                .map((x) => x.text)
                .includes(optionstring)
        ) {
            return;
        }
        option.text = optionstring;
        this.theList.add(option);
    }
}

function loadTagAutocomplete() {
    var rawFile = new XMLHttpRequest();
    rawFile.open("GET", "/static/OSMtag.txt", true);
    rawFile.onreadystatechange = function () {
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
    _mode;
    progressbar;
    progressbarLabel;
    message;
    _majorMax;
    _majorValue;
    _minorValue;
    _minorMax;
    _modeCount;

    overpassTimeout;
    overpassCountdown;
    minorStep;
    use_overpass;
    currentPhase;

    updateValueDispatch = {
        osmapi: () => {
            this.updateOSMAPI();
        },
        mode: () => {
            this.updateMode();
        },
        default: () => {},
        overpass: () => {
            this.updateOverpass();
        },
    };
    constructor() {
        this.progressbar = document.getElementById("progressbar");
        this.progressbarLabel = document.getElementById("progressbarLabel");
        this.message = document.getElementById("progbarMessage");

        // majorValue: overpass phase is 1, OSM API phase is 1, each mode is 1
        this._majorMax = 0;
        this._majorValue = 0;
        // minorValue: 1 second of overpass time is 1, each OSM API feature is 1
        this._minorValue = 0;
        this._minorMax = 0;

        this._modeCount = 0;

        this.overpassTimeout = 120;
        this.minorStep = this.overpassTimeout;
        this.use_overpass = false;
        this.currentPhase = "default";
    }
    set mode(value) {
        this._mode = value;
        this.updateValue();
    }
    get mode() {
        return this._mode;
    }
    set mode_count(count) {
        // this.majorMax = count + 1 + this.use_overpass;
        this._modeCount = parseInt(count);
        this.updateMax();
    }
    get mode_count() {
        return this._modeCount;
    }

    // set majorMax(max) {
    //         this._majorMax = parseInt(max);
    //         this.updateMax();
    //     }
    // get majorMax() {
    //         return this._majorMax;
    //     }

    get majorMax() {
        return this.mode_count + this.use_overpass + 1;
    }
    get realMax() {
        return this.majorMax * this.minorStep;
    }
    get realValue() {
        return this.majorValue * this.minorStep + this.minorValue;
    }
    set majorValue(value) {
        this._majorValue = parseInt(value);
        this._minorValue = 0;
        this.updateValue();
    }
    get majorValue() {
        return this._majorValue;
    }
    set minorValue(value) {
        this._minorValue = parseInt(value);
        this.updateValue();
    }
    get minorValue() {
        return this._minorValue;
    }
    get minorMax() {
        return this._minorMax;
    }
    set minorMax(max) {
        this._minorMax = parseInt(max);
        this.updateValue();
    }
    set visible(flag) {
        if (flag) {
            this.progressbarLabel.style.display = "block";
        } else {
            this.progressbarLabel.style.display = "none";
        }
    }
    updateMax() {
        this.progressbar.max = this.realMax;
    }
    updateValue() {
        this.updateValueDispatch[this.currentPhase]();
    }

    startOverpass() {
        this.overpassCountdown = window.setInterval(() => {
            // this.incrementOverpass();
            if (this.minorValue < this.overpassTimeout) {
                this.minorValue++;
            } else {
                clearInterval(this.overpassCountdown);
                progress.message.innerText = "Overpass timeout";
            }
        }, 1000);
    }

    completeOverpass() {
        clearInterval(this.overpassCountdown);
        this.majorValue = 1;
    }

    // incrementOverpass() {
    //     if (this.minorValue < this.overpassTimeout) {
    //         this.minorValue++;
    //     }
    // }

    updateOSMAPI() {
        this.message.innerText =
            "Checking deleted features on OSM API (" +
            this.minorValue +
            "/" +
            this.minorMax +
            ")";
        this.progressbar.value = this.realValue;
        this.progressbar.innerText =
            "(" + this.minorValue + "/" + this.minorMax + ")";
    }
    updateMode() {
        this.message.innerText = "Analyzing " + this.mode;
        this.progressbar.value = this.realValue;
        this.progressbar.innerText =
            "(" + this.minorValue + "/" + this.minorMax + ")";
    }
    updateOverpass() {
        this.message.innerText =
            "Querying Overpass, " +
            (this.overpassTimeout - this.minorValue) +
            " seconds until timeout";
        this.progressbar.value = this.realValue;
        this.progressbar.innerText =
            this.overpassTimeout - this.minorValue + " seconds remain";
    }
}

class fileTypeSelector {
    boxes;
    fileExt;
    extensions = {
        excel: ".xlsx",
        geojson: ".geojson",
        csv: ".zip",
    };
    constructor() {
        this.boxes = Array.from(document.getElementsByName("file_format"));
        this.boxes.forEach((elem) => {
            elem.addEventListener("change", () => {
                this.extensionChange();
            });
        });

        this.fileExt = document.getElementById("fileExt");
        this.extensionChange();
    }
    get type() {
        return this.boxes.filter((e) => e.checked)[0].value;
    }
    set type(value) {
        if (!value) {
            return;
        }
        var selectedBox = this.boxes.filter((x) => x.value == value)[0];
        selectedBox.checked = true;
    }
    extensionChange() {
        this.fileExt.innerText = this.extensions[this.type];
    }
}

function sendData() {
    const FD = new FormData(mainform);
    var overpassCountdown;
    evsource = new SSE("/result", {
        payload: FD,
    });
    evsource.addEventListener("error", () => {
        console.log("error");
    });
    evsource.addEventListener("open", () => {
        console.log("SSE connection open");
    });
    evsource.addEventListener("message", (e) => {
        console.log("message " + e.data);
    });
    evsource.addEventListener("overpass_start", (e) => {
        progress.currentPhase = "overpass";
        // progress.majorMax = 1 + progress.mode_count;
        progress.overpassTimeout = parseInt(e.data);
        progress.minorMax = parseInt(e.data);
        progress.visible = true;
        progress.startOverpass();
        // overpassCountdown = setInterval(function() {
        //     progress.minorValue++;
        // }, 1000);
        progress.updateValue();
    });
    evsource.addEventListener("overpass_complete", () => {
        clearInterval(overpassCountdown);
        progress.majorValue = 1;
        progress.updateValue();
    });
    evsource.addEventListener("overpass_failed", () => {
        clearInterval(overpassCountdown);
        // progress.completeOverpass();
        progress.message.innerText = "Overpass timeout";
        // progress.updateValue();
    });
    evsource.addEventListener("mode_count", (e) => {
        progress.mode_count = parseInt(e.data);
        // progress.majorMax = parseInt(e.data);
        progress.visible = true;
        progress.updateValue();
    });
    evsource.addEventListener("osm_api_max", (e) => {
        progress.currentPhase = "osmapi";
        progress.minorMax = parseInt(e.data);
    });
    evsource.addEventListener("osm_api_value", (e) => {
        progress.currentPhase = "osmapi";
        progress.minorValue = parseInt(e.data);
        progress.updateValue();
    });
    evsource.addEventListener("mode", (e) => {
        if (e.data != progress.mode) {
            // Don't change if for some reason it's redundant
            progress.majorValue++;
            progress.currentPhase = "mode";
            progress.mode = e.data;
            progress.updateValue();
        }
    });
    evsource.addEventListener("file", (e) => {
        progress.majorValue++;
        progress.message.innerText = "Analysis complete!";
        getFile(e);
    });

    // evsource.addEventListener("max", (e) => {
    //     progress.max = (parseInt(e.data) + 1) * progress.overpassTimeout;
    //     progress.visible = true;
    // });
    // evsource.addEventListener("value", (e) => {
    //     progress.value = (parseInt(e.data) + 1) * progress.overpassTimeout;
    // });
    evsource.stream();
}

var evsource;

var tagAutocomplete = document.getElementById("tagAutocomplete");
var mainform = document.getElementById("mainform");

var easyTabDiv = document.getElementById("easytab");

var manualTabDiv = document.getElementById("manualtab");
var manualInputs = manualTabDiv.getElementsByTagName("input");

var locationInput = document.getElementsByName("location")[0];
var startDateInput = document.getElementsByName("startdate")[0];
var endDateInput = document.getElementsByName("enddate")[0];
var outputInput = document.getElementsByName("output")[0];

var filterListGroup = new FilterList("filter");
var tagListGroup = new ItemList("tag", true);
var progress = new Progbar();

var fileTypeInstance = new fileTypeSelector();

var fileType = localStorage.getItem("file_format") ?? "excel";
fileTypeInstance.type = fileType;
// Initial value on load
tagListGroup.onTagListChange();

loadTagAutocomplete();
onTabChange();
window.addEventListener("hashchange", onTabChange);
mainform.addEventListener("submit", (event) => {
    event.preventDefault();
    if (document.activeElement.id == "tagAddField") {
        tagListGroup.addToList();
    } else if (
        document.activeElement.id == "filterAddField" ||
        document.activeElement.id == "filterValueField" ||
        document.activeElement.name == "filterTypeBox"
    ) {
        filterListGroup.addToList();
    } else {
        // Enable native validation and use it
        mainform.novalidate = false;
        var isValid = mainform.reportValidity();
        // Disable native validation so the above works again
        mainform.novalidate = true;
        if (!isValid) {
            return;
        }
        onSubmit(filterListGroup);
        onSubmit(tagListGroup);
        sendData();
    }
});

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
    localStorage.setItem("location", locationInput.value);
    localStorage.setItem("startdate", startDateInput.value);
    localStorage.setItem("enddate", endDateInput.value);
    localStorage.setItem("output", outputInput.value);
    localStorage.setItem("file_format", fileTypeInstance.type);
}

function getFile(event) {
    var path = event.data;
    window.location.pathname = "/download/" + path;
}

function askUserForConfirmation(message) {
    // TODO Finish this function
}
