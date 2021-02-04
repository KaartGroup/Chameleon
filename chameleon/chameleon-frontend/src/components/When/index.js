import React, { useContext } from "react";
import { Wrapper, Heading, FormWrapper, Label, Calander } from "./styles";
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";
import { ChameleonContext } from "../../common/ChameleonContext";
import calander from "../../images/calander.svg"; 
// TODO styling
export const When = () => {
    const { startDate, setStartDate, endDate, setEndDate } = useContext(ChameleonContext);

    return (
        <>
            <Wrapper>
                <Heading> When<Calander src={calander} alt="calander IMG"/></Heading>
            </Wrapper>
            <FormWrapper>
                <Label>
                    Start Date:
                <DatePicker
                    selected={startDate}
                    minDate={new Date("2012", "08", "12")}
                    maxDate={endDate}
                    name="startdate"
                    onChange={(date) => setStartDate(date)}
                />
                </Label>
                <Label>
                    End Date:
                <DatePicker
                    selected={endDate}
                    minDate={startDate}
                    maxDate={new Date()}
                    name="enddate"
                    onChange={(date) => setEndDate(date)}
                />
                </Label>
            </FormWrapper>
        </>
    );
};
