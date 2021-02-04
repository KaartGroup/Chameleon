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
import {
    FormWrapper,
    Form
} from "./styles"
// TODO styling
export const Chameleon = () => {
    const { progressDialogueRef } = useContext(ChameleonContext);

    return (
        <>
            <div className="progressModal" ref={progressDialogueRef} style={{ display: "none", height: "100px", width: "25%", position: "absolute", alignItems: "center", padding: "10px", backgroundColor: "white", border: "1px solid black", top: "50%", left: "50%", WebkitTransform: "translate(-50%, -50%)", transform: "translate(-50%, -50%)" }}>
                <ProgressBar />
            </div>
            <FormWrapper>
                <Form>
                    <Where />
                    <When />
                </Form>
                <Form>
                    <What />
                </Form>
                <Form>
                    <How />
                </Form>
                <Form>
                    <FileDetails />
                    <SubmitForm />
                </Form>
            </FormWrapper>
        </>
    );
};
