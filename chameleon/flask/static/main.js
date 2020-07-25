import { SSE } from "/static/sse.js";

function $(id) {
    return document.getElementById(id);
}

class ItemList {
    addField;
    addButton;
    removeButton;
    theList;
    required;
    constructor(name, required = false) {
        this.addField = document.getElementById(name + "AddField");
        this.addButton = document.getElementById(name + "AddButton");
        this.removeButton = document.getElementById(name + "RemoveButton");
        this.clearButton = document.getElementById(name + "ClearButton");
        this.theList = document.getElementById(name + "List");
        this.required = required;

        this.addButton.addEventListener("click", () => {
            this.addFromAddField();
        });
        this.removeButton.addEventListener("click", () => {
            this.removeFromList();
        });
        this.clearButton.addEventListener("click", () => {
            this.clearList();
        });
    }
    get asArray() {
        return Array.from(this.theList.options).map((x) => x.text);
    }
    addFromAddField() {
        /*
        Sends whatever value to the add func from the input field
        and clears the field
        */
        let fieldValue = this.addField.value;
        this.addField.value = "";
        this.addToList(fieldValue);
    }
    addToList(rawText) {
        /*
        Takes whatever value(s) is given, parses into multiple delimited inputs,
        and adds to the list
        */
        let items = rawText.trim().split(/[\s,|]+/);
        if (!items) {
            return;
        }

        for (let item of items) {
            if (this.asArray.includes(item)) {
                continue;
            }
            let option = document.createElement("option");
            option.text = item;
            this.theList.add(option);
        }
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

class HighDeletionsOk {
    input;
    dialog;
    constructor() {
        this.input = document.getElementsByName("high_deletions_ok")[0];
        this.dialog = $("highdeletionsdialog");
        $("highdeletionsyes").addEventListener("click", () => {
            this.respond(true);
        });
        $("highdeletionsno").addEventListener("click", () => {
            this.dialog.close();
        });
    }
    respond(answer) {
        if (answer) {
            this.input.disabled = false;
            let event = new Event("submit", {
                bubbles: true,
                cancelable: true,
            });
            $("mainform").dispatchEvent(event);
            this.input.disabled = true;
        }
        this.dialog.close();
    }
    askUser(message) {
        $("highdeletionstext").innerText = message;
        this.dialog.showModal();
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
        if (this.asArray.includes(optionstring)) {
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
                $("tagAutocomplete").append(option);
            }
        }
    };
    rawFile.send();
}

class Progbar {
    progressbar;
    progressbarDialog;
    message;
    _mode;
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
        this.progressbarDialog = document.getElementById("progressbarDialog");
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
            // this.progressbarDialog.style.display = "block";
            this.progressbarDialog.open = true;
        } else {
            // this.progressbarDialog.style.display = "none";
            this.progressbarDialog.open = false;
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

class FileTypeSelector {
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

class Shortcuts {
    defaultTags = ["highway", "name", "ref", "addr:housenumber", "addr:street"];
    loadedFavs;
    tagListObject;
    counter;
    constructor(tagListObject) {
        this.tagListObject = tagListObject;
        this.counter = favLoader();
        this.loadedFavs = Shortcuts.counter_to_array(this.counter);
        this.fillFavs();
    }
    fillFavs() {
        let difference = 5 - this.loadedFavs.length;
        if (difference > 0) {
            let toBeAdded = this.defaultTags
                .filter((x) => !this.loadedFavs.includes(x))
                .slice(0, 2);
            this.loadedFavs.concat(toBeAdded);
        }
    }
    createButtons() {
        for (let x of this.loadedFavs) {
            this.add(x);
        }
    }
    add(tag) {
        let item = document.createElement("li");
        let button = document.createElement("button");
        button.id = tag + "Shortcut";
        button.type = "button";
        button.innerText = tag;
        button.addEventListener("click", () => {
            this.tagListObject.addToList(tag);
        });
        item.appendChild(button);
        // item.innerHTML =
        //     '<button type="button" id="' + tag + 'Shortcut">' + tag + "</button>";
        $("favButtons").appendChild(item);
    }
    static counter_to_array(input) {
        let intermediate = [];
        for (let item in input) {
            intermediate.push([item, input[item]]);
        }
        intermediate.sort(function (a, b) {
            return a[1] - b[1];
        });
        return Array.from(intermediate.map((x) => x[0]).reverse());
    }
}

function addArray(obj, array) {
    for (let x of array) {
        let value = obj[x] ?? 0;
        obj[x] = value + 1;
    }
}

function sendData() {
    const FD = new FormData($("mainform"));
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
    evsource.addEventListener("high_deletion_percentage", (e) => {
        high_deletions_instance.askUser(e.data);
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

var high_deletions_instance = new HighDeletionsOk();

var evsource;

var manualInputs = $("manualtab").getElementsByTagName("input");

var locationInput = document.getElementsByName("location")[0];
var startDateInput = document.getElementsByName("startdate")[0];
var endDateInput = document.getElementsByName("enddate")[0];
var outputInput = document.getElementsByName("output")[0];

var filterListGroup = new FilterList("filter");
var tagListGroup = new ItemList("tag", true);
var progress = new Progbar();

var fileTypeInstance = new FileTypeSelector();

var shortcutsInstance = new Shortcuts(tagListGroup);
shortcutsInstance.createButtons();

var fileType = localStorage.getItem("file_format") ?? "excel";
fileTypeInstance.type = fileType;
// Initial value on load
tagListGroup.onTagListChange();

loadTagAutocomplete();
onTabChange();
window.addEventListener("hashchange", onTabChange);
$("mainform").addEventListener("submit", (event) => {
    event.preventDefault();
    if (document.activeElement.id == "tagAddField") {
        tagListGroup.addFromAddField();
    } else if (
        document.activeElement.id == "filterAddField" ||
        document.activeElement.id == "filterValueField" ||
        document.activeElement.name == "filterTypeBox"
    ) {
        filterListGroup.addToList();
    } else {
        // Enable native validation and use it
        $("mainform").novalidate = false;
        var isValid = $("mainform").reportValidity();
        // Disable native validation so the above works again
        $("mainform").novalidate = true;
        if (!isValid) {
            return;
        }
        addArray(shortcutsInstance.counter, tagListGroup.asArray);
        saveToLocalStorage();

        onSubmit(filterListGroup);
        onSubmit(tagListGroup);

        sendData();
    }
});

function onTabChange() {
    var isManualTab = window.location.hash == "#manualtab";
    $("easytab").disabled = isManualTab;
    $("manualtab").disabled = !isManualTab;

    // Cleans the URL of unnecessary hash
    if (window.location.hash == "") {
        history.replaceState(null, "", window.location.href.split("#")[0]);
    }
}

function onSubmit(object) {
    for (let x of object.theList.options) {
        x.selected = true;
    }
}

function saveToLocalStorage() {
    localStorage.setItem("location", locationInput.value);
    localStorage.setItem("startdate", startDateInput.value);
    localStorage.setItem("enddate", endDateInput.value);
    localStorage.setItem("output", outputInput.value);
    localStorage.setItem("file_format", fileTypeInstance.type);
    localStorage.setItem("counter", JSON.stringify(shortcutsInstance.counter));
}

function getFile(event) {
    var path = event.data;
    window.location.pathname = "/download/" + path;
}

function favLoader() {
    return JSON.parse(localStorage.getItem("counter")) ?? new Object();
}

function isObject(value) {
    return Object(value) === value;
}
