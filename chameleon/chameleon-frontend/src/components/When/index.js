import React, { useContext } from "react";
import { Wrapper, Heading } from "./styles";
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";
import { ChameleonContext } from "../../common/ChameleonContext";

// TODO styling
export const When = () => {
    const { startDate, setStartDate, endDate, setEndDate } = useContext(ChameleonContext);

    return (
        <>
            <Wrapper>
                <Heading> When </Heading>
            </Wrapper>
            <div
                style={{
                    display: "grid",
                    justifyContent: "center",
                    alignItems: "center",
                    paddingBottom: "10vh",
                }}
            >
                <p
                    style={{
                        display: "flex",
                        justifyContent: "center",
                        fontSize: "12px",
                    }}
                >
                    Start Date:
                </p>
                <DatePicker
                    selected={startDate}
                    minDate={new Date("2012", "08", "12")}
                    maxDate={endDate}
                    name="startdate"
                    onChange={(date) => setStartDate(date)}
                />
                <br></br>
                <p
                    style={{
                        display: "flex",
                        justifyContent: "center",
                        fontSize: "12px",
                    }}
                >
                    End Date:
                </p>
                <DatePicker
                    selected={endDate}
                    minDate={startDate}
                    maxDate={new Date()}
                    name="enddate"
                    onChange={(date) => setEndDate(date)}
                />
            </div>
        </>
    );
};
