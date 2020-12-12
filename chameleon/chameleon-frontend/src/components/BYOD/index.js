import React, { useContext, useState } from "react";
import Button from "@material-ui/core/Button";

import { FileDetails } from "../FileDetails";
import { How } from "../How";
import { Heading, Wrapper } from "./styles";
import { SubmitForm } from "../Submit";
import { ChameleonContext } from "../../common/ChameleonContext";
import { ProgressBar } from "../ProgressBar";

// TODO styling
export const BYOD = () => {
    const { oldFile, setOldFile, newFile, setNewFile , progressDialogueRef} = useContext(ChameleonContext);

    return (
    <>
        <div className="progressModal" ref={progressDialogueRef} style={{ display: "none", height: "100px", width: "25%", position: "absolute", alignItems: "center", padding: "10px", backgroundColor: "white", border: "1px solid black", top: "50%", left: "50%", WebkitTransform: "translate(-50%, -50%)", transform: "translate(-50%, -50%)" }}>
            <ProgressBar />
        </div>
        <form style={{ display: "flex", width: "100vw", flexDirection: "row", flexWrap: "wrap", justifyContent:"center" }}>
            <div style={{ border: "1px solid black", width: "23vw", marginTop: "2.5%", marginBottom: "2.5%", marginRight: "2.5%" }}>
                <Wrapper>
                    <Heading>
                        <abbr
                            style={{ textDecoration: "none" }}
                            title="Bring Your Own Data"
                        >
                            BYOD
                        </abbr>
                    </Heading>
                </Wrapper>
                <div style={{ display: "flex", justifyContent: "center", marginTop: "30px" }}>
                    <Button variant="contained" component="label">
                        Old File
                        <input
                            type="file"
                            hidden
                            onChange={(e) => {
                                setOldFile(e.target.value);
                            }}
                        />
                    </Button>
                    <Button variant="contained" component="label">
                        New File
                        <input type="file"
                            hidden
                            onChange={(e) => { 
                                setNewFile(e.target.value);
                            }}
                        />
                    </Button>
                </div>
                <How />
            </div>
            <div style={{ border: "1px solid black", width: "23vw", marginTop: "2.5%", marginBottom: "2.5%", marginLeft: "2.5%" }}>
                <FileDetails />
                <SubmitForm />
            </div>
        </form>
    </>
    );
};
