import React from "react";
import {
    Wrapper,
    Heading,
    StyledLabel,
} from "./styles";

export const SubmitForm = () => {

    const submitForm = () => {
        console.log('submitting form!');
    }

    return (
      <>
        <Wrapper>
          <Heading> Submit </Heading>
        </Wrapper>
        <div style={{ display: "grid", justifyContent: "center", alignContent: "center", height: "40%" }}>
        <StyledLabel>
            Group by rows of change:
            <input type="checkbox" value="n" name="filterTypeBox" defaultChecked=""/>
          </StyledLabel>
          <br></br>
            <button type="submit" onClick={submitForm}>Run</button>
        </div>
      </>
    );
};