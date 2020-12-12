import React, { createContext, useState, useRef, useEffect } from "react";
import { useLocalStorageState } from "../LocalStorageState";
import $ from 'jquery';
window.$ = $;

export const ChameleonContext = createContext({});

export const ChameleonProvider = ({ children }) => {
  const API_URL = "http://localhost:5000/";

  const [where, setWhere] = useState('BZ');
  const [oldFile, setOldFile] = useState(null);
  const [newFile, setNewFile] = useState(null);
  const [startDate, setStartDate] = useState(new Date('02/27/2020'));
  const [endDate, setEndDate] = useState(new Date('03/03/2020'));
  const [keyVal, setKeyVal] = useState([]);
  const [tags, setTags] = useState([]);
  const [fileName, setFileName] = useState("chameleon");
  const [fileType, setFileType] = useState("excel");
  const [grouping, setGrouping] = useState(false);
  const [isBYOD, setIsBYOD] = useState(false);

  var overpassIntervalID;  
  const [chameleonEventSource, setChameleonEventSource] = useState(null);
  const [progbar, setProgbar] = useState();
  const [label, setLabel] = useState(null);
  const progressDialogueRef = useRef();
  const progressBarRef = useRef();
  const cancelRef = useRef();
  const [UUID, setUUID] = useLocalStorageState("client_uuid", null);

  useEffect(() => {
    if (UUID != null && chameleonEventSource == null) {
      setChameleonEventSource(new EventSource(API_URL + "longtask_status/" + UUID));
      setProgbar(new Progbar());
    }
  }, []);

  useEffect(() => {
    if (UUID != null) {
      setChameleonEventSource(new EventSource(API_URL + "longtask_status/" + UUID));
      setProgbar(new Progbar());
    }
  }, [UUID]);

  useEffect(() => {
    if (chameleonEventSource != null) {
      chameleonEventSource.addEventListener("error", () => {
        console.log("error");
      });
      chameleonEventSource.addEventListener("open", () => {
          console.log("SSE connection open");
      });
      chameleonEventSource.addEventListener("message", (event) => {
          console.log(`message ${event.data}`);
      });
      checkStatus(chameleonEventSource);
    }
  }, [chameleonEventSource])

  const isValid = () => {
    return where !== "" && keyVal.length >= 0 && tags.length > 0 && isBYOD != null && !isBYOD;
  } 

  const isValidBYOD = () => {
    return tags.length > 0 && isBYOD != null && isBYOD;
  }

  const submit = (e) => {
    e.preventDefault();

    if (isValid) {
      fetch(API_URL + "result", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          location: where,
          startdate: startDate,
          enddate: endDate,
          file_format: fileType,
          output: fileName,
          job_uuid: UUID,
          modes: tags,
          filter_list: keyVal,
          grouping: grouping,
          high_deletions_ok: false,
        }),
    })
      .then((response) => response.json())
      .then((jsonResponse) => {
        setUUID(jsonResponse["client_uuid"]);
      });
    }
  }



function jsonReviver(key, value) {
    return ["overpass_start_time", "overpass_timeout_time"].includes(key)
        ? new Date(value)
        : value;
}

const cancelJob = () => {
  fetch(API_URL + "abort", {
      method: "DELETE",
      headers: new Headers({ "content-type": "application/json" }),
      body: JSON.stringify({ client_uuid: UUID }),
  }).then(
      (response) => {
          if (response.status == 200) {
              progbar.current_phase = "abort";
              progbar.updateMessage();
          }
      },
      () => {
          console.log("Task couldn't be canceled");
      }
  );
}

const endJob = () => {
  chameleonEventSource.close();
  setUUID(null);
}

const checkStatus = (chameleonEvent) => {
  let progress = progbar;

  chameleonEvent.addEventListener("task_update", (event) => {
      let taskStatus = JSON.parse(event.data, jsonReviver);
      if (taskStatus["state"] == "SUCCESS") {
        if (progressDialogueRef.current.style.display != "grid") {
          progressDialogueRef.current.style.display = "grid"
        }
          console.log("SUCCESS Closing SSE connection");
          progress.current_phase = "success";
          progress.updateMessage();
          endJob();
          window.setTimeout(function() { downloadFile(taskStatus); }, 5000);
        } else if (
            UUID &&
            taskStatus["state"] == "PENDING"
        ) {
            // PENDING means unknown to the task manager
            // Unless the UUID was recieved from the server, it's probably not valid
            console.log("Bad UUID given, closing SSE connection");
            endJob();
        } else if (
            UUID &&
            taskStatus["state"] == "FAILURE" &&
            taskStatus["deletion_percentage"]
        ) {
            // Task failed because of high deletion rate, indicating mismatched data
            //this.highDeletionsInstance.askUser(
            //    taskStatus["deletion_percentage"]
            //);
            console.log('task failed due to high deletion rate');
            endJob();
            
        } else if (taskStatus["state"] == "ABORTED") {
          console.log("Task aborted, closing SSE connection");
          endJob();
        } else if (taskStatus["state"] == "FAILURE") {
            // Other, unknown failure
            console.log(`Task failed with error: ${taskStatus["error"]}`, "Closing SSE connection");
            endJob();
        } 
        progress.updateMessage();
  });
}

const downloadFile = (taskStatus) => {
  let downloadURL = API_URL + "download/" + taskStatus["uuid"] + "/" + taskStatus["file_name"];
  fetch(downloadURL, {
    method: "GET",
    headers: new Headers({ "content-type": "application/octet-stream", "content-disposition": { "filename" : taskStatus["file_name"] } })
  })
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
  dialog;
  message;
  cancelButton;

  constructor() {
      this.progressbar = progressBarRef.current;
      this.dialog = progressDialogueRef;
      this.message = label;
      this.cancelButton = cancelRef.current;

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
      if (["success", "cancel", "failure","abort"].includes(this.current_phase)) {
          this.finished_message();
      } else {
          this.cancelButton.disabled = false;
          console.log('current_phase', this.current_phase);

          if (this.current_phase == "overpass") {
              overpassIntervalID = window.setInterval(() => {
                  if (this.overpassRemaining <= 0) {
                      window.clearInterval(overpassIntervalID);
                      this.current_phase = "failure";
                      this.finished_message();
                  } else {
                      this.overpass_message();
                  }
              }, 1000);
          } else {
              if (overpassIntervalID) {
                  window.clearInterval(overpassIntervalID);
              }
              this.progressDispatch[this.current_phase]();
          }
      }
      if (this.dialog ? this.dialog.current.style.display != "grid" : false) {
          this.dialog.current.style.display = "grid";
      }
  }

  finished_message() {
      this.cancelButton.disabled = true;
      setLabel(this.finishedDispatch[this.current_phase] + " Refresh the page to start a new query.");
      this.progressbar.value = this.progressbar.max = 1;
      this.progressbar.innerText = "";
  }

  progressDispatch = {
      init: () => {
        setLabel("Initiating…");
      },
      pending: () => {
        setLabel("Data recieved, beginning analysis…");
      },
      osm_api: () => this.osm_api_message(),
      modes: () => this.modes_message(),
  };

  finishedDispatch = {
      success: "Analysis complete!",
      cancel: "Analysis canceled!",
      failure: "Analysis failed!",
      abort: "Analysis aborted!",
  };

  overpass_message() {
    setLabel('Querying Overpass,' + this.overpassRemaining + 'seconds until timeout');
    this.progressbar.value = this.realValue;
    this.progressbar.max = this.realMax;
    this.progressbar.innerText = `${this.overpassRemaining} seconds remain`;
  }
  osm_api_message() {
      setLabel("Checking deleted features on OSM API (" + (this.osm_api_completed + 1/this.osm_api_max) + ")");
      this.progressbar.value = this.realValue;
      this.progressbar.max = this.realMax;
      this.progressbar.innerText = `(${this.osm_api_completed + 1}/${
          this.osm_api_max
      })`;
  }
  modes_message() {
      setLabel("Analyzing" + this.current_mode);
      this.progressbar.value = this.realValue;
      this.progressbar.max = this.realMax;
      this.progressbar.innerText = `(${this.modes_completed}/${this.mode_count})`;
  }
}

  const value = {
    where,
    setWhere,
    oldFile,
    setOldFile,
    newFile,
    setNewFile,
    startDate,
    setStartDate,
    endDate,
    setEndDate,
    keyVal,
    setKeyVal,
    tags,
    setTags,
    fileName,
    setFileName,
    fileType,
    setFileType,
    grouping,
    setGrouping,
    isBYOD,
    setIsBYOD,
    progressDialogueRef,
    progressBarRef,
    cancelRef,
    label,
    submit,
    cancelJob,
    UUID,
  };
  
    return value ? (
      <ChameleonContext.Provider value={value}>{children}</ChameleonContext.Provider>
    ) : null;
  
};