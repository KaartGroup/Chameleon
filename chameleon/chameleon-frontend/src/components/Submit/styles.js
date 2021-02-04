import styled from "styled-components";

export const Wrapper = styled.div`
    display: flex;
    border-bottom: 2px solid #f4753c;
    border-top: 2px solid #f4753c;
    background-color: white;
    border-radius: 6px;
    box-shadow: 0px 2px;
    // box-shadow-color: #f4753c;
    padding: 6px;
`;

export const Heading = styled.p`
    display: flex;
    font-family: "Hind Guntur",sans-serif;
    width: 100%;
    font-size: 20px;
    font-weight: bold;
    justify-content: center;
    align-items: center;
`;

export const FormWrapper = styled.div`
display: "grid",
justifyContent: "center",
alignContent: "center",
marginTop: "5%",
marginBottom: "5%",
padding: 15px;
// transform:translate(5%, 80%);
`;

export const SubmitInput = styled.input`
  padding: 12px 20px;
  margin: 8px 0;
  display: inline-block;
  border: 1px solid #ccc;
  border-radius: 6px;
  box-sizing: border-box;
`;

export const Label = styled.p`
font-size: 15px;
padding: 5px;
`;

export const Button = styled.button`
border-radius: 6px;
  border: 0;
  margin: 8px 80%;
  background-color: #f4753c;
  color: white;
  padding: 5px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
    &:hover {
        background-color: #c85823;
      }
`;
