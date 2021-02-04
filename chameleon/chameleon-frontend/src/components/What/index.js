import React, { useContext, useRef } from "react";
import { ChameleonContext } from "../../common/ChameleonContext";
import { Wrapper, Heading, WhatInput, FormWrapper, Label, Button, Title, WhatIMG } from "./styles";
import whatIMG from "../../images/whatIMG.svg"; 

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
                <Heading> 
                    What<WhatIMG src={whatIMG} alt="what IMG"/> 
                </Heading>
            </Wrapper>
            <FormWrapper>
                <Title>
                    Filters
                </Title>
                <Label>
                    Key:
                    <WhatInput
                        type="text"
                        placeholder="OSM Key"
                        ref={keyRef}
                    />
                </Label>
                <Label>
                    Values(s):
                    <WhatInput
                        type="text"
                        placeholder="OSM Value(s)"
                        pattern="[A-z:,| ]"
                        title="Separate multiple values with commas (,), spaces, or pipes (|). Use asterisk (*) for all values"
                        ref={valueRef}
                    />
                    </Label>
                <Label>
                    Node:
                    <WhatInput
                        type="checkbox"
                        defaultChecked="y"
                        ref={nodeRef}
                    />
                    </Label>
                <Label>
                    Way:
                    <WhatInput
                        type="checkbox"
                        defaultChecked="y"
                        ref={wayRef}
                    />
                    </Label>
                <Label>
                    Relation:
                    <WhatInput
                        type="checkbox"
                        defaultChecked="y"
                        ref={relRef}
                    />
                    </Label>
                <Button onClick={(e) => { 
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
                </Button>
                <Button onClick={(e) => {
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
                </Button>
                <Button onClick={(e) => { e.preventDefault(); selectRef.current.length = 0; setKeyVal([]); }}>Clear</Button>
                <select size="5" name="filter_list" multiple="" ref={selectRef}></select>
                <br></br>
            </FormWrapper>
        </>
    );
};
