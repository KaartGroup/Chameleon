import React from "react";
import { Where } from "../Where";
import { When } from "../When";
import { What } from "../What";
import { How } from "../How";
import { FileDetails } from "../FileDetails";
import { SubmitForm } from "../Submit";
import "./styles.css";

export const Chameleon = () => {
    return (
        <>
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
