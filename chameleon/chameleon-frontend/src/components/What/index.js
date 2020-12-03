import React, { useContext, useRef } from "react";
import { ChameleonContext } from "../../common/ChameleonContext";
import { Wrapper, Heading, StyledLabel } from "./styles";

// TODO maybe autocomplete key and values for key?
// TODO verify key and (maybe) values
// TODO styling
export const What = () => {
    const keyRef = useRef();
    const valueRef = useRef();
    const selectRef = useRef();
    const nodeRef = useRef();
    const wayRef = useRef();
    const relRef = useRef();

    const { keyVal, setKeyVal } = useContext(ChameleonContext);
    
    return (
        <>
            <Wrapper>
                <Heading> What </Heading>
            </Wrapper>
            <div
                style={{
                    display: "grid",
                    justifyContent: "center",
                    alignItems: "center",
                    height: "80%",
                }}
            >
                <p
                    style={{
                        display: "flex",
                        justifyContent: "center",
                        fontSize: "12px",
                    }}
                >
                    Filters
                </p>

                <StyledLabel>
                    Key:
                    <input
                        type="text"
                        placeholder="OSM Key"
                        ref={keyRef}
                    />
                </StyledLabel>

                <br></br>

                <StyledLabel>
                    Values(s):
                    <input
                        type="text"
                        placeholder="OSM Value(s)"
                        pattern="[A-z:,| ]"
                        title="Separate multiple values with commas (,), spaces, or pipes (|). Use asterisk (*) for all values"
                        ref={valueRef}
                    />
                </StyledLabel>

                <br></br>
                <br></br>

                <StyledLabel>
                    Node:
                    <input
                        type="checkbox"
                        defaultChecked="y"
                        ref={nodeRef}
                    />
                </StyledLabel>

                <br></br>

                <StyledLabel>
                    Way:
                    <input
                        type="checkbox"
                        defaultChecked="y"
                        ref={wayRef}
                    />
                </StyledLabel>

                <br></br>

                <StyledLabel>
                    Relation:
                    <input
                        type="checkbox"
                        defaultChecked="y"
                        ref={relRef}
                    />
                </StyledLabel>
                <br></br>
                <br></br>
                <button onClick={(e) => { 
                    e.preventDefault();
                    
                    if (keyRef.current.value !== "" && valueRef.current.value !== "") {
                        var item = [
                            keyRef.current.value.trim(),
                            valueRef.current.value.trim().split(/[\s,|]+/),
                            [nodeRef.current.checked ? "n" : "", wayRef.current.checked ? "w" : "", relRef.current.checked ? "r" : ""],
                        ];
                    
                        const found = ["w", "n", "r"].some(r=> item[2].includes(r))

                        if (found) {
                            // TODO verify key has only one value
                            item = item.filter((x) => x);
                            var keyValue = [item[0], item[1].join(",")].filter((x) => x).join("=");
                            var option = document.createElement("option");
                            var optionString = `${keyValue} (${item[2].join("")})`;

                            option.text = optionString;
                            selectRef.current.add(option);
                            setKeyVal(keyVal.concat(optionString));
                            keyRef.current.value = "";
                            valueRef.current.value = "";
                        }     
                    }

                }}>
                    Add
                </button>
                <button onClick={(e) => {
                    e.preventDefault();

                    if (selectRef.current.selectedIndex === -1) {
                        selectRef.current.setCustomValidity("Please select a tag to remove");
                        selectRef.current.reportValidity();
                        selectRef.current.setCustomValidity("");
                        return;
                    }
                    
                    var index = keyVal.indexOf(selectRef.current.options[selectRef.current.selectedIndex].value);
                    keyVal.splice(index, 1);
                    selectRef.current.remove(selectRef.current.selectedIndex);
                    setKeyVal(keyVal);
                }}>
                    Remove
                </button>
                <button onClick={(e) => { e.preventDefault(); selectRef.current.length = 0; setKeyVal([]); }}>Clear</button>
                <select size="5" name="filter_list" multiple="" ref={selectRef}></select>
                <br></br>
            </div>
        </>
    );
};
