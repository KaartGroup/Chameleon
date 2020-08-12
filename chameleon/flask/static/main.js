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
        this.addField = $(name + "AddField");
        this.addButton = $(name + "AddButton");
        this.removeButton = $(name + "RemoveButton");
        this.clearButton = $(name + "ClearButton");
        this.theList = $(name + "List");
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
            this.theList.setCustomValidity(
                !this.theList.options.length
                    ? "Please add at least one item!"
                    : ""
            );
        }
    }
    selectAll() {
        for (let x of this.theList.options) {
            x.selected = true;
        }
    }
}

class FilterList extends ItemList {
    constructor(name, required = false) {
        super(name, required);
        this.valueField = $(name + "ValueField");
        this._typeArray = document.getElementsByName(name + "TypeBox");
    }
    get typeArray() {
        return Array.from(this._typeArray);
    }
    addFromAddField() {
        var item = [
            this.addField.value.trim(),
            this.valueField.value.trim().split(/[\s,|]+/),
            this.typeArray.filter((a) => a.checked).map((a) => a.value),
        ];
        if (!item[0]) {
            return;
        }
        item = item.filter((x) => x);
        var keyValue = [item[0], item[1].join(",")].filter((x) => x).join("=");
        this.addField.value = "";
        this.valueField.value = "";
        var option = document.createElement("option");
        var optionString = `${keyValue} (${item[2].join("")})`;
        if (this.asArray.includes(optionString)) {
            return;
        }
        option.text = optionString;
        this.theList.add(option);
    }
}

class HighDeletionsOk {
    input;
    dialog;
    constructor() {
        this.input = $("high_deletions_ok");
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
    askUser(percentage) {
        $(
            "highdeletionstext"
        ).innerText = `There is an unusually high proportion of deletions (${percentage}%). This often indicates that the two input files have different scope. Would you like to continue?`;
        this.dialog.showModal();
    }
}

class Progbar {
    // Snake case properties are direct from the server, camelCase are internal only
    current_mode;
    current_phase;
    mode_count;
    modes_completed;
    osm_api_completed;
    osm_api_max;
    overpass_start_time;
    overpass_timeout_time;

    progressbar;
    progressbarDialog;
    message;

    constructor() {
        this.progressbar = $("progressbar");
        this.progressbarDialog = $("progressbarDialog");
        this.message = $("progressbarMessage");

        this.overpass_start_time = this.overpass_timeout_time = null;
        this.osm_api_completed = this.osm_api_max = this.modes_completed = 0;
        this.current_phase = "init";
    }

    get usingOverpass() {
        return (
            this.overpass_start_time !== null &&
            this.overpass_timeout_time !== null
        );
    }
    get overpassElapsed() {
        // Return whole seconds elapsed
        return this.usingOverpass
            ? Math.round((new Date() - this.overpass_start_time) / 1000)
            : 0;
    }
    get overpassRemaining() {
        // Return whole seconds until timeout
        return this.usingOverpass
            ? Math.max(
                  Math.round((this.overpass_timeout_time - new Date()) / 1000),
                  0
              )
            : 0;
    }
    get overpassTimeout() {
        // Deduce the server's original timeout setting
        return Math.round(
            (this.overpass_timeout_time - this.overpass_start_time) / 1000
        );
    }
    get realMax() {
        return this.overpassTimeout + this.osm_api_max + this.mode_count * 10;
    }
    get realValue() {
        return (
            this.overpassElapsed +
            this.osm_api_completed +
            this.modes_completed * 10
        );
    }

    updateMessage() {
        if (this.current_phase == "overpass") {
            overpassIntervalID = window.setInterval(() => {
                if (this.overpassRemaining <= 0) {
                    window.clearInterval(overpassIntervalID);
                    this.failure_message();
                } else {
                    this.overpass_message();
                }
            }, 1000);
        } else {
            if (overpassIntervalID) {
                window.clearInterval(overpassIntervalID);
            }
            this.phaseDispatch[this.current_phase]();
        }
        if (this.realMax) {
            this.progressbar.max = this.realMax;
        }
        if (!progress.progressbarDialog.open) {
            progress.progressbarDialog.showModal();
        }
    }

    phaseDispatch = {
        init: () => {
            this.message.innerText = "Initiating…";
        },
        pending: () => {
            this.message.innerText = "Data recieved, beginning analysis…";
        },
        // overpass: () => this.overpass_message(),
        osm_api: () => this.osm_api_message(),
        modes: () => this.modes_message(),
        complete: () => this.complete_message(),
    };

    overpass_message() {
        this.message.innerText = `Querying Overpass, ${this.overpassRemaining} seconds until timeout`;
        this.progressbar.value = this.realValue;
        this.progressbar.innerText = `${this.overpassRemaining} seconds remain`;
    }
    osm_api_message() {
        this.message.innerText = `Checking deleted features on OSM API (${
            this.osm_api_completed + 1
        }/${this.osm_api_max})`;
        this.progressbar.value = this.realValue;
        this.progressbar.innerText = `(${this.osm_api_completed + 1}/${
            this.osm_api_max
        })`;
    }
    modes_message() {
        this.message.innerText = `Analyzing ${this.current_mode}`;
        this.progressbar.value = this.realValue;
        this.progressbar.innerText = `(${this.modes_completed}/${this.mode_count})`;
    }
    complete_message() {
        this.message.innerText = "Analysis complete!";
        this.progressbar.value = this.realMax;
        this.progressbar.innerText = "100%";
    }
    failure_message() {
        this.message.innerText = "Analysis failed!";
        this.progressbar.value = this.progressbar.max = 1;
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
                this.extensionUpdate();
            });
        });

        this.fileExt = $("fileExt");
        this.extensionUpdate();
    }
    get type() {
        return this.boxes.filter((e) => e.checked)[0].value;
    }
    set type(value) {
        if (!value) {
            return;
        }
        this.boxes.filter((x) => x.value == value)[0].checked = true;
    }
    extensionUpdate() {
        this.fileExt.innerText = this.extensions[this.type];
    }
}

class Shortcuts {
    shortcutCount = 5;
    defaultTags = ["highway", "name", "ref", "addr:housenumber", "addr:street"];
    loadedFavs;
    tagListObject;
    counter;
    constructor(tagListObject) {
        this.tagListObject = tagListObject;
        this.counter =
            JSON.parse(localStorage.getItem("counter")) ?? new Object();
        this.loadedFavs = Shortcuts.counterToArray(this.counter).slice(
            0,
            this.shortcutCount
        );
        this.fillFavs();
    }
    fillFavs() {
        let difference = this.shortcutCount - this.loadedFavs.length;
        if (difference > 0) {
            let toBeAdded = this.defaultTags
                .filter((x) => !this.loadedFavs.includes(x))
                .slice(0, difference);
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
        $("favButtons").appendChild(item);
    }
    static counterToArray(input) {
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

function loadTagAutocomplete() {
    fetch("/static/OSMtag.txt")
        .then((response) => response.text())
        .then((rawText) => {
            for (let i of rawText.split("\n")) {
                let option = document.createElement("option");
                option.value = i;
                $("tagAutocomplete").append(option);
            }
        });
}

function addArray(obj, array) {
    for (let key of array) {
        obj[key] = (obj[key] ?? 0) + 1;
    }
}

function checkStatus(task_id, recieved_id = true) {
    var evsource = new EventSource(`/longtask_status/${task_id}`);

    evsource.addEventListener("error", () => {
        console.log("error");
    });
    evsource.addEventListener("open", () => {
        console.log("SSE connection open");
    });
    evsource.addEventListener("message", (event) => {
        console.log(`message ${event.data}`);
    });
    evsource.addEventListener("task_update", (event) => {
        let taskStatus = JSON.parse(event.data, jsonReviver);

        if (taskStatus["state"] == "SUCCESS") {
            window.location.pathname = `/download/${taskStatus["uuid"]}/${taskStatus["file_name"]}`;
            console.log("Closing SSE connection");
            evsource.close();
            localStorage.removeItem("client_uuid");
            progress.current_phase = "complete";
        } else if (taskStatus["state"] == "PENDING" && !recieved_id) {
            // PENDING means unknown to the task manager
            // Unless the UUID was recieved from the server, it's probably not valid
            console.log("Bad UUID given, closing SSE connection");
            evsource.close();
            localStorage.removeItem("client_uuid");
        } else if (
            taskStatus["state"] == "FAILURE" &&
            taskStatus["deletion_percentage"]
        ) {
            // Task failed because of high deletion rate, indicating mismatched data
            highDeletionsInstance.askUser(taskStatus["deletion_percentage"]);
            evsource.close();
            localStorage.removeItem("client_uuid");
        } else if (taskStatus["state"] == "FAILURE") {
            // Other, unknown failure
            console.log(`Task failed with error: ${taskStatus["error"]}`);
            console.log("Closing SSE connection");
            evsource.close();
            localStorage.removeItem("client_uuid");
        } else {
            Object.assign(progress, taskStatus);
        }
        progress.updateMessage();
    });
}

function jsonReviver(key, value) {
    return key in ["overpass_start_time", "overpass_timeout_time"]
        ? new Date(value)
        : value;
}

function sendData() {
    fetch("/result", {
        method: "POST",
        body: new FormData($("mainform")),
    })
        .then((response) => response.json())
        .then((jsonResponse) => {
            setUuid(jsonResponse["client_uuid"]);
            checkStatus(jsonResponse["client_uuid"]);
        });
}

function setUuid(uuid) {
    if (
        uuid.match(
            /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
        )
    ) {
        localStorage.setItem("client_uuid", uuid);
    }
}

function onTabChange() {
    var isManualTab = window.location.hash == "#manualtab";
    $("easytab").disabled = isManualTab;
    $("manualtab").disabled = !isManualTab;

    // Cleans the URL of unnecessary hash
    if (window.location.hash == "") {
        history.replaceState(null, "", window.location.href.split("#")[0]);
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

function onSubmit(event) {
    event.preventDefault();
    if (document.activeElement.id == "tagAddField") {
        tagListGroup.addFromAddField();
    } else if (
        document.activeElement.id == "filterAddField" ||
        document.activeElement.id == "filterValueField" ||
        document.activeElement.name == "filterTypeBox"
    ) {
        filterListGroup.addFromAddField();
    } else {
        // Enable native validation and use it
        $("mainform").novalidate = false;
        let isValid = $("mainform").reportValidity();
        // Disable native validation so the above works again
        $("mainform").novalidate = true;
        if (!isValid) {
            return;
        }
        addArray(shortcutsInstance.counter, tagListGroup.asArray);
        saveToLocalStorage();

        // Show message so user knows their input was accepted
        progress.updateMessage();

        filterListGroup.selectAll();
        tagListGroup.selectAll();

        sendData();
    }
}

var overpassIntervalID;

const locationInput = document.getElementsByName("location")[0];
const startDateInput = document.getElementsByName("startdate")[0];
const endDateInput = document.getElementsByName("enddate")[0];
const outputInput = document.getElementsByName("output")[0];

var highDeletionsInstance = new HighDeletionsOk();
var filterListGroup = new FilterList("filter");

var tagListGroup = new ItemList("tag", true);
// Initial value on load
tagListGroup.onTagListChange();

var progress = new Progbar();

var fileTypeInstance = new FileTypeSelector();
fileTypeInstance.type = localStorage.getItem("file_format") ?? "excel";

var shortcutsInstance = new Shortcuts(tagListGroup);
shortcutsInstance.createButtons();

var clientUuid = localStorage.getItem("client_uuid");
if (clientUuid) {
    checkStatus(clientUuid, false);
}

loadTagAutocomplete();
onTabChange();
window.addEventListener("hashchange", onTabChange);
$("mainform").addEventListener("submit", onSubmit);
