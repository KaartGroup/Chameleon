import React, { useContext } from "react";
import { ChameleonContext } from "../../common/ChameleonContext";

export const ProgressBar = () => {
  const { progressBarRef, label, cancelJob, cancelRef } = useContext(ChameleonContext);
  
    return (
    <>
    <p>{label}</p>
    <br></br>
      <progress style={{ width: "100%" }} ref={progressBarRef} />
      <button ref={cancelRef} onClick={() => { cancelJob(); }} disabled="">Cancel</button>
    </>
    );
};

  