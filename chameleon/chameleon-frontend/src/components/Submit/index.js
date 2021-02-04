import React, { useContext, useState } from "react";
import { ChameleonContext } from "../../common/ChameleonContext";
import { Wrapper, Heading, SubmitInput, FormWrapper, Label, Button  } from "./styles";

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
            <FormWrapper>
                <Label>
                    Group by rows of change:
                    <SubmitInput
                        type="checkbox"
                        value="n"
                        name="filterTypeBox"
                        onChange={() => setGrouping(!grouping)}
                    />
                </Label>
                <Button type="submit" onClick={submit}>
                    Run
                </Button>
            </FormWrapper>
        </>
    );
};
