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

class FilterList extends ItemList {
    constructor(name, required = false) {
        super(name, required);
        this.valueField = document.getElementById(name + "ValueField");
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
    askUser(percentage) {
        let message =
            "There is an unusually high proportion of deletions (" +
            percentage +
            "%). " +
            "This often indicates that the two input files have different scope. " +
            "Would you like to continue?";
        $("highdeletionstext").innerText = message;
        this.dialog.showModal();
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

class Progbar {
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

    phaseDispatch = {
        init: () => this.initial_message(),
        pending: () => this.pending_message(),
        overpass: () => this.overpass_message(),
        osm_api: () => this.osm_api_message(),
        modes: () => this.modes_message(),
        complete: () => this.complete_message(),
    };

    constructor() {
        this.progressbar = $("progressbar");
        this.progressbarDialog = $("progressbarDialog");
        this.message = $("progressbarMessage");

        this.overpass_start_time = this.overpass_timeout_time = null;
        this.modes_completed = 0;
        this.current_phase = "init";
    }

    updateMessage() {
        this.phaseDispatch[this.current_phase]();
        if (this.realMax) {
            this.progressbar.max = this.realMax;
        }
        if (!progress.progressbarDialog.open) {
            progress.progressbarDialog.showModal();
        }
    }

    initial_message() {
        this.message.innerText = "Initiating...";
    }
    pending_message() {
        this.message.innerText = "Data recieved, beginning analysis...";
    }
    overpass_message() {
        this.message.innerText =
            "Querying Overpass, " +
            this.overpassRemaining +
            " seconds until timeout";
        this.progressbar.value = this.realValue;
        this.progressbar.innerText = this.overpassRemaining + " seconds remain";
    }
    osm_api_message() {
        this.message.innerText =
            "Checking deleted features on OSM API (" +
            (this.osm_api_completed + 1) +
            "/" +
            this.osm_api_max +
            ")";
        this.progressbar.value = this.realValue;
        this.progressbar.innerText =
            "(" + (this.osm_api_completed + 1) + "/" + this.osm_api_max + ")";
    }
    modes_message() {
        this.message.innerText = "Analyzing " + this.current_mode;
        this.progressbar.value = this.realValue;
        this.progressbar.innerText =
            "(" + this.modes_completed + "/" + this.mode_count + ")";
    }
    complete_message() {
        this.message.innerText = "Analysis complete!";
        this.progressbar.value = this.realMax;
        this.progressbar.innerText = "100%";
    }
    get usingOverpass() {
        return (
            this.overpass_start_time !== null &&
            this.overpass_timeout_time !== null
        );
    }

    get overpassElapsed() {
        // Return whole seconds elapsed
        if (this.usingOverpass) {
            return Math.round((new Date() - this.overpass_start_time) / 1000);
        } else {
            return 0;
        }
    }
    get overpassRemaining() {
        // Return whole seconds until timeout
        if (this.usingOverpass) {
            return Math.max(
                Math.round((this.overpass_timeout_time - new Date()) / 1000),
                0
            );
        } else {
            return 0;
        }
    }
    get overpassTimeout() {
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
    shortcutCount = 5;
    defaultTags = ["highway", "name", "ref", "addr:housenumber", "addr:street"];
    loadedFavs;
    tagListObject;
    counter;
    constructor(tagListObject) {
        this.tagListObject = tagListObject;
        this.counter = favLoader();
        this.loadedFavs = Shortcuts.counter_to_array(this.counter).slice(
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

function checkStatus(task_id) {
    evsource = new EventSource("/longtask_status/" + task_id);

    evsource.addEventListener("error", () => {
        console.log("error");
    });
    evsource.addEventListener("open", () => {
        console.log("SSE connection open");
    });
    evsource.addEventListener("message", (e) => {
        console.log("message " + e.data);
    });
    evsource.addEventListener("task_update", (e) => {
        task_status = JSON.parse(e.data, jsonReviver);
        Object.assign(progress, task_status);
        progress.updateMessage();
    });
    evsource.addEventListener("task_complete", (e) => {
        // progress.message.innerText = "Analysis complete!";
        task_status = JSON.parse(e.data, jsonReviver);
        Object.assign(progress, task_status);
        progress.updateMessage();

        getFile(task_status["uuid"] + "/" + task_status["file_name"]);

        console.log("Closing SSE connection");
        evsource.close();
    });
    evsource.addEventListener("high_deletion_percentage", (e) => {
        high_deletions_instance.askUser(e.data);
    });
}

function jsonReviver(key, value) {
    if (key in ["overpass_start_time", "overpass_timeout_time"]) {
        return new Date(value);
    }
    return value;
}

function sendData() {
    const FD = new FormData($("mainform"));
    fetch("/result", {
        method: "POST",
        body: FD,
    })
        .then((response) => response.json())
        .then((jsonResponse) => {
            set_uuid(jsonResponse["client_uuid"]);
            checkStatus(jsonResponse["client_uuid"]);
        });
}

function set_uuid(uuid) {
    if (
        uuid.match(
            /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
        )
    ) {
        localStorage.setItem("client_uuid", uuid);
        $("client_uuid").value = uuid;
    }
}

var high_deletions_instance = new HighDeletionsOk();

var evsource;
var task_status;

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

var client_uuid = localStorage.getItem("client_uuid");
// Disabled until better system for managing jobs by client is implemented
// if (client_uuid) {
//     $("client_uuid").value = client_uuid;
// }

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
        filterListGroup.addFromAddField();
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

        // Show message so user knows their input was accepted
        progress.updateMessage();

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

function getFile(path) {
    window.location.pathname = "/download/" + path;
}

function favLoader() {
    return JSON.parse(localStorage.getItem("counter")) ?? new Object();
}

function isObject(value) {
    return Object(value) === value;
}
