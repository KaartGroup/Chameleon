import styled from "styled-components";

export const Wrapper = styled.div`
    display: flex;
    border-top: 1px dashed black;
`;

export const Heading = styled.p`
    display: flex;
    width: 100%;
    text-decoration: underline #f4753c;
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
`;

export const Button = styled.button`
border-radius: 6px;
  border: 0;
  margin: 8px 0px;
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
