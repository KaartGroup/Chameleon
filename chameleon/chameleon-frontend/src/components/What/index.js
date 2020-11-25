import React from "react";
import {
    Wrapper,
    Heading,
    StyledLabel,
} from "./styles";

export const What = () => {
    return (
      <div>
        <Heading> What </Heading>
          <p style={{ display: "flex", justifyContent: "center", fontSize: "12px" }}>Filters</p>

          <StyledLabel> 
            Key: 
            <input type="text" placeholder="OSM Key" onChange={() => console.log('handling OSM Key change')} />
          </StyledLabel>

          <br></br>
          
          <StyledLabel>
            Values(s):
            <input type="text" placeholder="OSM Value(s)" pattern="[A-z:,| ]" title="Separate multiple values with commas (,), spaces, or pipes (|). Use asterisk (*) for all values" onChange={() => console.log('handling OSM Key change')} />
          </StyledLabel>
          
          <br></br>
          <br></br>
          
          <StyledLabel>
            Node:
            <input type="checkbox" value="n" name="filterTypeBox" defaultChecked=""/>
          </StyledLabel>
          
          <br></br>
          
          <StyledLabel>
            Way:
            <input type="checkbox" value="n" name="filterTypeBox" defaultChecked=""/>
          </StyledLabel>
          
          <br></br>
          
          <StyledLabel>
            Relation:
            <input type="checkbox" value="n" name="filterTypeBox" defaultChecked=""/>
          </StyledLabel>
          <br></br>
          <br></br>
          <button onClick={() => console.log('add')}>Add</button>
          <button onClick={() => console.log('remove')}>Remove</button>
          <button onClick={() => console.log('clear')}>Clear</button>
          <select size="5" multiple=""></select>
          
          <br></br>
      </div>
    );
};