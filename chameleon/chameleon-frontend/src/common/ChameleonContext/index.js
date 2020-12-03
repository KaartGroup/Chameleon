import React, { createContext, useState, useRef } from "react";

export const ChameleonContext = createContext({});

export const ChameleonProvider = ({ children }) => {
  const API_URL = "http://localhost:5000/";

  const [jobState, setJobState] = useState(null);

  const [where, setWhere] = useState(null);

  const [oldFile, setOldFile] = useState(null);

  const [newFile, setNewFile] = useState(null);

  const [startDate, setStartDate] = useState(new Date());

  const [endDate, setEndDate] = useState(new Date());

  const [keyVal, setKeyVal] = useState([]);

  const [tags, setTags] = useState([]);

  const [fileName, setFileName] = useState("chameleon");

  const [fileType, setFileType] = useState(".xlsx");

  const [grouping, setGrouping] = useState(false);

  const [isBYOD, setIsBYOD] = useState(false);

  // fetch job uid onPageLoad
  const fetchJob = () => {
    if (getUUID()) {
      console.log('fetching job with uuid', getUUID());
      let jobURL = API_URL + "longtask_status/" + getUUID();
      let streaming = false;

      fetch(jobURL)
        .then((response) => {
          if (!response.ok) throw response;
          if (streaming) {
            const reader = response.body.getReader();
            let string = "";
            let index = 1;
            let job_state = "";
            reader
              .read()
              .then(function processJson({ done, value }) {
                if (done) {
                  reader.releaseLock();
                  return;
                }
                for (var i = 0; i < value.byteLength; i++) {
                  let character = value[i]; 
                  if (character !== 0x1e && character !== 0x0a) {
                    string += String.fromCharCode(character);
                  } else if (string.length > 0) {
                    console.log('string',string);
                    string = "";
                  }
                }
                return reader.read().then(processJson);
              })
              .finally((data) => {
                console.log(data);
                //setJobState(job_state);
              });
          } else {
            response.json().then((data) => setJobState(data));
          }
        })
        .catch((error) => {
          console.log('ERROR in fetching job status:', error);
        })
    }
  };

  const submit = (e) => {
    e.preventDefault();

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
        job_uuid: getUUID(),
        modes: tags,
        filter_list: keyVal,
        grouping: grouping,
        high_deletions_ok: false,
      }),
  })
    .then((response) => response.json())
    .then((jsonResponse) => {
      setUUID(jsonResponse["client_uuid"]);
      // long task api call here vv
      //this.checkStatus(this.uuid);
    }).then(fetchJob);
  }


  const setUUID = (uuid) => {
    if (uuid.match(/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i))
      localStorage.setItem("client_uuid", uuid);
  }
  
  const getUUID = () => {
    return localStorage.getItem("client_uuid");
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
    submit,
    fetchJob,
    getUUID,
  };
  
    return value ? (
      <ChameleonContext.Provider value={value}>{children}</ChameleonContext.Provider>
    ) : null;
  
};