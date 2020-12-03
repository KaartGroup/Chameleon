import React, { createContext, useState } from "react";

export const ChameleonContext = createContext({});

export const ChameleonProvider = ({ children }) => {

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
  };
  
    return value ? (
      <ChameleonContext.Provider value={value}>{children}</ChameleonContext.Provider>
    ) : null;
  
};