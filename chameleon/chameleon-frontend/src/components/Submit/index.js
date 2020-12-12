import React, { useContext, useState } from "react";
import { ChameleonContext } from "../../common/ChameleonContext";
import { Wrapper, Heading, StyledLabel } from "./styles";

// TODO styling
export const SubmitForm = () => {
    const {
        grouping,
        setGrouping,
        submit,
    } = useContext(ChameleonContext);

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
