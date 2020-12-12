import React, { useEffect, useContext } from "react";
import { Where } from "../Where";
import { When } from "../When";
import { What } from "../What";
import { How } from "../How";
import { FileDetails } from "../FileDetails";
import { SubmitForm } from "../Submit";
import "./styles.css";
import { ChameleonContext } from "../../common/ChameleonContext";
import { ProgressBar } from "../ProgressBar";

// TODO styling
export const Chameleon = () => {
    const { progressDialogueRef } = useContext(ChameleonContext);

    return (
        <>
            <div className="progressModal" ref={progressDialogueRef} style={{ display: "none", height: "100px", width: "25%", position: "absolute", alignItems: "center", padding: "10px", backgroundColor: "white", border: "1px solid black", top: "50%", left: "50%", WebkitTransform: "translate(-50%, -50%)", transform: "translate(-50%, -50%)" }}>
                <ProgressBar />
            </div>
            <form style={{ display: "flex", width: "100vw", flexDirection: "row", flexWrap: "wrap", justifyContent:"space-around" }}>
                <div style={{border: "1px solid black", width: "23vw", marginTop: "2.5%", marginBottom: "2.5%"}}>
                    <Where />
                    <When />
                </div>
                <div style={{border: "1px solid black", width: "23vw", marginTop: "2.5%", marginBottom: "2.5%"}}>
                    <What />
                </div>
                <div style={{border: "1px solid black", width: "23vw", marginTop: "2.5%", marginBottom: "2.5%"}}>
                    <How />
                </div>
                <div style={{border: "1px solid black", width: "23vw", marginTop: "2.5%", marginBottom: "2.5%"}}>
                    <FileDetails />
                    <SubmitForm />
                </div>
            </form>
        </>
    );
};
