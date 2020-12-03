import React, { useContext, useState } from "react";
import { ChameleonContext } from "../../common/ChameleonContext";
import { Wrapper, Heading, StyledLabel } from "./styles";

// TODO styling
export const SubmitForm = () => {
    const {
        where,
        startDate,
        endDate,
        keyVal,
        tags,
        fileName,
        fileType,
        grouping,
        setGrouping,
        isBYOD,
    } = useContext(ChameleonContext);

    const submit = (e) => {
        e.preventDefault();

        if (isValid()) {
            console.log("valid S-B-S",where, startDate, endDate, keyVal, tags, fileName, fileType, "grouping:", grouping, "isBYOD:", isBYOD);
        } else if (isValidBYOD()) {
            console.log("valid BYOD", where, startDate, endDate, keyVal, tags, fileName, fileType, "grouping:", grouping, "isBYOD:", isBYOD);
        }
    }

    const isValid = () => {
        return where !== "" && keyVal.length > 0 && tags.length > 0 && isBYOD != null;
    } 

    const isValidBYOD = () => {
        return tags.length > 0 && isBYOD != null;
    }

    return (
        <>
            <Wrapper>
                <Heading> Submit </Heading>
            </Wrapper>
            <div
                style={{
                    display: "grid",
                    justifyContent: "center",
                    alignContent: "center",
                    marginTop: "5%",
                    marginBottom: "5%",
                }}
            >
                <StyledLabel>
                    Group by rows of change:
                    <input
                        type="checkbox"
                        value="n"
                        name="filterTypeBox"
                        onChange={() => setGrouping(!grouping)}
                    />
                </StyledLabel>
                <br></br>
                <button type="submit" onClick={submit}>
                    Run
                </button>
            </div>
        </>
    );
};
